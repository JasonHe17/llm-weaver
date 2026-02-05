"""
API Key 管理接口
提供API Key的创建、查询、更新、删除等功能
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db
from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import logger
from app.core.security import generate_api_key, hash_api_key, mask_api_key
from app.db.models.api_key import APIKey
from app.db.models.user import User as UserModel
from app.schemas import (
    APIKeyCreate,
    APIKeyCreateResponse,
    APIKeyListResponse,
    APIKeyResponse,
    APIKeyUpdate,
    PaginatedResponse,
    ResponseModel,
)

router = APIRouter()


def api_key_to_response(key: APIKey) -> APIKeyResponse:
    """将API Key ORM对象转换为响应模型.
    
    Args:
        key: API Key ORM对象
        
    Returns:
        APIKeyResponse: 响应模型
    """
    return APIKeyResponse(
        id=key.id,
        name=key.name,
        key_mask=mask_api_key(key.key_hash),  # 使用哈希值生成遮罩
        status=key.status,
        budget_limit=float(key.budget_limit),
        budget_used=float(key.budget_used),
        rate_limit=key.rate_limit,
        allowed_models=key.allowed_models,
        expires_at=key.expires_at,
        last_used_at=key.last_used_at,
        created_at=key.created_at,
    )


@router.get("", response_model=ResponseModel[APIKeyListResponse])
async def list_api_keys(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="状态筛选"),
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """获取API Key列表.
    
    只返回当前用户创建的API Keys
    
    Args:
        page: 页码
        page_size: 每页数量
        status: 状态筛选
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        API Key列表（分页）
    """
    # 构建查询
    query = select(APIKey).where(APIKey.user_id == current_user.id)
    
    if status:
        query = query.where(APIKey.status == status)
    
    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # 分页查询
    query = query.order_by(APIKey.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    api_keys = result.scalars().all()
    
    # 构建响应
    items = [api_key_to_response(key) for key in api_keys]
    total_pages = (total + page_size - 1) // page_size
    
    return ResponseModel(
        code=200,
        message="success",
        data=APIKeyListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ),
    )


@router.post("", response_model=ResponseModel[APIKeyCreateResponse], status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: APIKeyCreate,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """创建新的API Key.
    
    注意：API Key只会在创建时完整显示一次，请妥善保存
    
    Args:
        request: 创建请求
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        包含完整API Key的响应（仅一次）
    """
    # 生成新的API Key
    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)
    
    # 创建记录
    api_key = APIKey(
        user_id=current_user.id,
        key_hash=key_hash,
        name=request.name,
        status="active",
        budget_limit=request.budget_limit,
        budget_used=0,
        rate_limit=request.rate_limit,
        allowed_models=request.allowed_models,
        expires_at=request.expires_at,
    )
    
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    
    logger.info(f"API Key created: {api_key.id} for user {current_user.id}")
    
    return ResponseModel(
        code=201,
        message="API Key创建成功",
        data=APIKeyCreateResponse(
            id=api_key.id,
            key=raw_key,  # 仅创建时返回完整Key
            name=api_key.name,
            created_at=api_key.created_at,
        ),
    )


@router.get("/{key_id}", response_model=ResponseModel[APIKeyResponse])
async def get_api_key(
    key_id: int,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """获取API Key详情.
    
    Args:
        key_id: API Key ID
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        API Key详情
        
    Raises:
        NotFoundError: API Key不存在
    """
    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.user_id == current_user.id,
        )
    )
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        raise NotFoundError("API Key不存在")
    
    return ResponseModel(
        code=200,
        message="success",
        data=api_key_to_response(api_key),
    )


@router.put("/{key_id}", response_model=ResponseModel[APIKeyResponse])
async def update_api_key(
    key_id: int,
    request: APIKeyUpdate,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """更新API Key.
    
    支持更新名称、状态、预算限制等
    
    Args:
        key_id: API Key ID
        request: 更新请求
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        更新后的API Key
        
    Raises:
        NotFoundError: API Key不存在
    """
    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.user_id == current_user.id,
        )
    )
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        raise NotFoundError("API Key不存在")
    
    # 更新字段
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(api_key, field, value)
    
    await db.commit()
    await db.refresh(api_key)
    
    logger.info(f"API Key updated: {key_id} by user {current_user.id}")
    
    return ResponseModel(
        code=200,
        message="API Key更新成功",
        data=api_key_to_response(api_key),
    )


@router.delete("/{key_id}", response_model=ResponseModel[dict])
async def delete_api_key(
    key_id: int,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """删除API Key.
    
    软删除：将状态设置为 revoked
    
    Args:
        key_id: API Key ID
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        删除成功消息
        
    Raises:
        NotFoundError: API Key不存在
    """
    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.user_id == current_user.id,
        )
    )
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        raise NotFoundError("API Key不存在")
    
    # 软删除
    api_key.status = "revoked"
    await db.commit()
    
    logger.info(f"API Key revoked: {key_id} by user {current_user.id}")
    
    return ResponseModel(
        code=200,
        message="API Key已删除",
        data={"message": "API Key已成功撤销"},
    )


@router.post("/{key_id}/revoke", response_model=ResponseModel[APIKeyResponse])
async def revoke_api_key(
    key_id: int,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """撤销API Key（与删除相同）.
    
    Args:
        key_id: API Key ID
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        撤销后的API Key
    """
    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.user_id == current_user.id,
        )
    )
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        raise NotFoundError("API Key不存在")
    
    api_key.status = "revoked"
    await db.commit()
    await db.refresh(api_key)
    
    logger.info(f"API Key revoked: {key_id} by user {current_user.id}")
    
    return ResponseModel(
        code=200,
        message="API Key已撤销",
        data=api_key_to_response(api_key),
    )


@router.post("/{key_id}/regenerate", response_model=ResponseModel[APIKeyCreateResponse])
async def regenerate_api_key(
    key_id: int,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """重新生成API Key.
    
    生成新的API Key，旧Key立即失效
    
    Args:
        key_id: API Key ID
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        包含新API Key的响应（仅一次）
        
    Raises:
        NotFoundError: API Key不存在
    """
    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.user_id == current_user.id,
        )
    )
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        raise NotFoundError("API Key不存在")
    
    # 生成新的API Key
    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)
    
    # 更新密钥哈希
    api_key.key_hash = key_hash
    api_key.status = "active"
    await db.commit()
    await db.refresh(api_key)
    
    logger.info(f"API Key regenerated: {key_id} by user {current_user.id}")
    
    return ResponseModel(
        code=200,
        message="API Key重新生成成功",
        data=APIKeyCreateResponse(
            id=api_key.id,
            key=raw_key,  # 仅重新生成时返回完整Key
            name=api_key.name,
            created_at=api_key.created_at,
        ),
    )
