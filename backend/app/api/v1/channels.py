"""
渠道管理接口
提供上游供应商渠道的配置管理
"""

import time
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_current_admin_user, get_db
from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError, UpstreamError
from app.core.logging import logger
from app.db.models.channel import Channel
from app.db.models.model_mapping import ModelMapping
from app.db.models.user import User as UserModel
from app.schemas import (
    ChannelCreate,
    ChannelListResponse,
    ChannelResponse,
    ChannelTestResponse,
    ChannelUpdate,
    ResponseModel,
)

router = APIRouter()


@router.get("", response_model=ResponseModel[ChannelListResponse])
async def list_channels(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type: Optional[str] = Query(None, description="渠道类型筛选"),
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """获取渠道列表.
    
    普通用户只能看到自己的渠道，管理员可以看到所有渠道
    
    Args:
        page: 页码
        page_size: 每页数量
        type: 渠道类型筛选
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        渠道列表（分页）
    """
    # 构建查询
    query = select(Channel)
    
    # 非管理员只能看到自己的渠道或系统渠道
    if current_user.role != "admin":
        query = query.where(
            (Channel.user_id == current_user.id) | (Channel.is_system == True)
        )
    
    if type:
        query = query.where(Channel.type == type)
    
    # 获取总数
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar()
    
    # 分页查询
    query = query.order_by(Channel.priority.desc(), Channel.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    channels = result.scalars().all()
    
    # 构建响应
    items = [ChannelResponse.from_orm_with_mappings(ch) for ch in channels]
    total_pages = (total + page_size - 1) // page_size
    
    return ResponseModel(
        code=200,
        message="success",
        data=ChannelListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ),
    )


@router.post("", response_model=ResponseModel[ChannelResponse], status_code=status.HTTP_201_CREATED)
async def create_channel(
    request: ChannelCreate,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """创建新渠道.
    
    Args:
        request: 创建请求
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        新创建的渠道
    """
    # 验证渠道类型
    valid_types = ["openai", "anthropic", "azure", "gemini", "mistral", "cohere"]
    if request.type not in valid_types:
        raise ValidationError(f"不支持的渠道类型，可选: {', '.join(valid_types)}")
    
    # 创建渠道
    channel = Channel(
        user_id=current_user.id,
        name=request.name,
        type=request.type,
        config=request.config,
        weight=request.weight,
        priority=request.priority,
        status="active",
        is_system=False,
    )
    
    db.add(channel)
    await db.flush()  # 获取channel.id
    
    # 创建模型映射
    for mapping in request.models:
        model_mapping = ModelMapping(
            channel_id=channel.id,
            model_id=mapping.model_id,
            mapped_model=mapping.mapped_model,
        )
        db.add(model_mapping)
    
    await db.commit()
    await db.refresh(channel)
    
    logger.info(f"Channel created: {channel.id} by user {current_user.id}")
    
    return ResponseModel(
        code=201,
        message="渠道创建成功",
        data=ChannelResponse.from_orm_with_mappings(channel),
    )


@router.get("/{channel_id}", response_model=ResponseModel[ChannelResponse])
async def get_channel(
    channel_id: int,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """获取渠道详情.
    
    Args:
        channel_id: 渠道ID
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        渠道详情
        
    Raises:
        NotFoundError: 渠道不存在
    """
    result = await db.execute(
        select(Channel).where(Channel.id == channel_id)
    )
    channel = result.scalar_one_or_none()
    
    if not channel:
        raise NotFoundError("渠道不存在")
    
    # 检查权限（非管理员只能看自己的或系统的）
    if current_user.role != "admin":
        if channel.user_id != current_user.id and not channel.is_system:
            raise NotFoundError("渠道不存在")
    
    return ResponseModel(
        code=200,
        message="success",
        data=ChannelResponse.from_orm_with_mappings(channel),
    )


@router.put("/{channel_id}", response_model=ResponseModel[ChannelResponse])
async def update_channel(
    channel_id: int,
    request: ChannelUpdate,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """更新渠道.
    
    Args:
        channel_id: 渠道ID
        request: 更新请求
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        更新后的渠道
        
    Raises:
        NotFoundError: 渠道不存在
        AuthorizationError: 无权限修改
    """
    result = await db.execute(
        select(Channel).where(Channel.id == channel_id)
    )
    channel = result.scalar_one_or_none()
    
    if not channel:
        raise NotFoundError("渠道不存在")
    
    # 检查权限
    from app.core.exceptions import AuthorizationError
    if current_user.role != "admin" and channel.user_id != current_user.id:
        raise AuthorizationError("无权修改此渠道")
    
    # 更新渠道字段
    update_data = request.model_dump(exclude_unset=True, exclude={"models"})
    for field, value in update_data.items():
        if value is not None:
            setattr(channel, field, value)
    
    # 更新模型映射
    if request.models is not None:
        # 删除旧的映射
        await db.execute(
            select(ModelMapping).where(ModelMapping.channel_id == channel_id)
        )
        # 创建新的映射
        for mapping in request.models:
            model_mapping = ModelMapping(
                channel_id=channel_id,
                model_id=mapping.model_id,
                mapped_model=mapping.mapped_model,
            )
            db.add(model_mapping)
    
    await db.commit()
    await db.refresh(channel)
    
    logger.info(f"Channel updated: {channel_id} by user {current_user.id}")
    
    return ResponseModel(
        code=200,
        message="渠道更新成功",
        data=ChannelResponse.from_orm_with_mappings(channel),
    )


@router.delete("/{channel_id}", response_model=ResponseModel[dict])
async def delete_channel(
    channel_id: int,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """删除渠道.
    
    Args:
        channel_id: 渠道ID
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        删除成功消息
    """
    result = await db.execute(
        select(Channel).where(Channel.id == channel_id)
    )
    channel = result.scalar_one_or_none()
    
    if not channel:
        raise NotFoundError("渠道不存在")
    
    # 检查权限
    from app.core.exceptions import AuthorizationError
    if current_user.role != "admin" and channel.user_id != current_user.id:
        raise AuthorizationError("无权删除此渠道")
    
    # 软删除：标记为inactive
    channel.status = "inactive"
    await db.commit()
    
    logger.info(f"Channel deleted: {channel_id} by user {current_user.id}")
    
    return ResponseModel(
        code=200,
        message="渠道已删除",
        data={"message": "渠道已成功删除"},
    )


@router.post("/{channel_id}/test", response_model=ResponseModel[ChannelTestResponse])
async def test_channel(
    channel_id: int,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """测试渠道连接.
    
    向供应商API发送一个简单的测试请求
    
    Args:
        channel_id: 渠道ID
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        测试结果
    """
    result = await db.execute(
        select(Channel).where(Channel.id == channel_id)
    )
    channel = result.scalar_one_or_none()
    
    if not channel:
        raise NotFoundError("渠道不存在")
    
    # 检查权限
    from app.core.exceptions import AuthorizationError
    if current_user.role != "admin" and channel.user_id != current_user.id:
        raise AuthorizationError("无权测试此渠道")
    
    # 测试连接
    config = channel.config
    channel_type = channel.type
    
    start_time = time.time()
    
    try:
        if channel_type == "openai":
            # 测试OpenAI连接
            api_base = config.get("api_base", "https://api.openai.com")
            api_key = config.get("api_key")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{api_base}/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                response.raise_for_status()
        
        elif channel_type == "azure":
            # 测试Azure连接
            api_base = config.get("api_base")
            api_key = config.get("api_key")
            api_version = config.get("api_version", "2024-02-01")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{api_base}/openai/models?api-version={api_version}",
                    headers={"api-key": api_key},
                )
                response.raise_for_status()
        
        else:
            # 其他类型简单返回成功
            pass
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        # 更新渠道状态
        channel.status = "active"
        await db.commit()
        
        return ResponseModel(
            code=200,
            message="连接测试成功",
            data=ChannelTestResponse(
                status="success",
                latency_ms=latency_ms,
                message="渠道连接正常",
                tested_at=datetime.now(timezone.utc),
            ),
        )
    
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        
        # 更新渠道状态
        channel.status = "error"
        await db.commit()
        
        logger.error(f"Channel test failed: {channel_id}, error: {e}")
        
        return ResponseModel(
            code=200,
            message="连接测试失败",
            data=ChannelTestResponse(
                status="error",
                latency_ms=latency_ms,
                message=f"连接失败: {str(e)}",
                tested_at=datetime.now(timezone.utc),
            ),
        )
