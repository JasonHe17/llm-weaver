"""
模型管理接口
提供可用模型列表查询
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.api.deps import get_current_active_user, get_current_admin_user, get_db, get_current_api_key
from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import logger
from app.db.models.model_def import ModelDef
from app.db.models.channel import Channel
from app.db.models.user import User as UserModel
from app.schemas import ResponseModel, PaginatedResponse
from app.services.model_provider import fetch_models_from_channel, ProviderModel
from pydantic import BaseModel, Field
from datetime import datetime

router = APIRouter()


class ModelInfo(BaseModel):
    """模型信息."""
    
    id: str = Field(..., description="模型ID")
    name: str = Field(..., description="模型名称")
    provider: str = Field(..., description="供应商")
    capabilities: List[str] = Field(default=[], description="能力列表")
    context_window: int = Field(..., description="上下文窗口大小")
    pricing_input: float = Field(..., description="输入价格（每1K tokens）")
    pricing_output: float = Field(..., description="输出价格（每1K tokens）")
    status: str = Field(..., description="状态")


class ModelsListResponse(BaseModel):
    """模型列表响应."""
    
    items: List[ModelInfo]
    total: int


class ModelInfoResponse(BaseModel):
    """模型信息响应（适配前端）."""

    id: str = Field(..., description="模型ID")
    name: str = Field(..., description="模型名称")
    provider: str = Field(..., description="供应商")
    description: str = Field(default="", description="描述")
    status: str = Field(..., description="状态")
    pricing: dict = Field(default_factory=dict, description="价格信息")
    capabilities: List[str] = Field(default=[], description="能力列表")
    context_length: int = Field(default=0, description="上下文长度")
    created_at: str = Field(default="", description="创建时间")
    updated_at: str = Field(default="", description="更新时间")


class SyncModelsResponse(BaseModel):
    """同步模型响应."""

    provider: str = Field(..., description="供应商")
    channel_type: str = Field(..., description="渠道类型")
    models_added: int = Field(default=0, description="新增模型数")
    models_updated: int = Field(default=0, description="更新模型数")
    models_total: int = Field(default=0, description="总模型数")
    error: Optional[str] = Field(default=None, description="错误信息")


class SyncAllModelsResponse(BaseModel):
    """同步所有模型响应."""

    results: List[SyncModelsResponse] = Field(default=[], description="各供应商同步结果")
    total_added: int = Field(default=0, description="总新增模型数")
    total_updated: int = Field(default=0, description="总更新模型数")


@router.get("", response_model=ResponseModel[PaginatedResponse[ModelInfoResponse]])
async def list_models(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    provider: Optional[str] = Query(None, description="供应商筛选"),
    capability: Optional[str] = Query(None, description="能力筛选"),
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """获取可用模型列表（分页）.
    
    Args:
        page: 页码
        page_size: 每页数量
        provider: 供应商筛选
        capability: 能力筛选 (chat/vision/function_calling)
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        可用模型列表（分页）
    """
    query = select(ModelDef)
    
    if provider:
        query = query.where(ModelDef.provider == provider)
    
    if capability:
        query = query.where(ModelDef.capabilities.contains([capability]))
    
    # 总数
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar()
    
    # 分页
    query = query.order_by(ModelDef.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    models = result.scalars().all()
    
    items = [
        ModelInfoResponse(
            id=m.id,
            name=m.name,
            provider=m.provider,
            description=m.description or "",
            status=m.status,
            pricing={
                "input_price": float(m.pricing_input),
                "output_price": float(m.pricing_output),
            },
            capabilities=m.capabilities or [],
            context_length=m.context_window,
            created_at=m.created_at.isoformat() if m.created_at else "",
            updated_at=m.updated_at.isoformat() if m.updated_at else "",
        )
        for m in models
    ]
    
    total_pages = (total + page_size - 1) // page_size
    
    return ResponseModel(
        code=200,
        message="success",
        data=PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ),
    )


@router.get("/all", response_model=ResponseModel[List[ModelInfoResponse]])
async def list_all_active_models(
    refresh: bool = Query(False, description="是否从API刷新模型列表"),
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """获取所有活跃模型列表（不分页）.

    如果refresh=True，会尝试从已配置的渠道API获取最新模型列表，
    获取失败则返回数据库中的模型。

    Args:
        refresh: 是否从API刷新模型列表
        current_user: 当前用户
        db: 数据库会话

    Returns:
        活跃模型列表
    """
    # 如果请求刷新，尝试从API获取
    if refresh:
        try:
            api_models = await _fetch_models_from_all_channels(db)
            if api_models:
                return ResponseModel(
                    code=200,
                    message="success (from API)",
                    data=api_models,
                )
        except Exception as e:
            logger.warning(f"Failed to fetch models from APIs: {e}")

    # 从数据库获取
    result = await db.execute(
        select(ModelDef).where(ModelDef.status == "active")
    )
    models = result.scalars().all()

    items = [
        ModelInfoResponse(
            id=m.id,
            name=m.name,
            provider=m.provider,
            description=m.description or "",
            status=m.status,
            pricing={
                "input_price": float(m.pricing_input),
                "output_price": float(m.pricing_output),
            },
            capabilities=m.capabilities or [],
            context_length=m.context_window,
            created_at=m.created_at.isoformat() if m.created_at else "",
            updated_at=m.updated_at.isoformat() if m.updated_at else "",
        )
        for m in models
    ]

    return ResponseModel(
        code=200,
        message="success (from database)",
        data=items,
    )


@router.get("/{model_id}", response_model=ResponseModel[ModelInfo])
async def get_model(
    model_id: str,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """获取模型详情.

    Args:
        model_id: 模型ID
        current_user: 当前用户
        db: 数据库会话

    Returns:
        模型详情

    Raises:
        NotFoundError: 模型不存在
    """
    result = await db.execute(
        select(ModelDef).where(ModelDef.id == model_id)
    )
    model = result.scalar_one_or_none()

    if not model:
        raise NotFoundError("模型不存在")

    return ResponseModel(
        code=200,
        message="success",
        data=ModelInfo(
            id=model.id,
            name=model.name,
            provider=model.provider,
            capabilities=model.capabilities or [],
            context_window=model.context_window,
            pricing_input=float(model.pricing_input),
            pricing_output=float(model.pricing_output),
            status=model.status,
        ),
    )


async def _fetch_models_from_all_channels(
    db: AsyncSession,
) -> Optional[List[ModelInfoResponse]]:
    """从所有活跃渠道获取模型列表.

    Args:
        db: 数据库会话

    Returns:
        合并后的模型列表，如果都失败则返回None
    """
    # 获取所有活跃渠道
    result = await db.execute(
        select(Channel).where(Channel.status == "active")
    )
    channels = result.scalars().all()

    all_models: List[ModelInfoResponse] = []
    seen_models = set()

    for channel in channels:
        try:
            config = channel.config
            provider_models = await fetch_models_from_channel(
                channel_type=channel.type,
                api_key=config.get("api_key", ""),
                api_base=config.get("api_base"),
                api_version=config.get("api_version"),
                organization=config.get("organization"),
            )

            for pm in provider_models:
                if pm.id not in seen_models:
                    seen_models.add(pm.id)
                    all_models.append(ModelInfoResponse(
                        id=pm.id,
                        name=pm.name,
                        provider=pm.provider,
                        description=pm.description,
                        status="active",
                        pricing={
                            "input_price": 0.0,
                            "output_price": 0.0,
                        },
                        capabilities=pm.capabilities or ["chat"],
                        context_length=pm.context_window or 0,
                        created_at="",
                        updated_at="",
                    ))

            logger.info(f"Fetched {len(provider_models)} models from {channel.type} channel: {channel.name}")

        except Exception as e:
            logger.warning(f"Failed to fetch models from {channel.type} channel {channel.name}: {e}")
            continue

    return all_models if all_models else None


@router.post("/sync", response_model=ResponseModel[SyncAllModelsResponse])
async def sync_models_from_providers(
    channel_id: Optional[int] = Query(None, description="指定渠道ID（默认所有活跃渠道）"),
    current_user: UserModel = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """从供应商API同步模型列表到数据库.

    管理员接口，从已配置的渠道API获取模型列表并更新到数据库。

    Args:
        channel_id: 指定渠道ID（默认同步所有活跃渠道）
        current_user: 当前管理员用户
        db: 数据库会话

    Returns:
        同步结果统计
    """
    # 构建查询
    query = select(Channel).where(Channel.status == "active")
    if channel_id:
        query = query.where(Channel.id == channel_id)

    result = await db.execute(query)
    channels = result.scalars().all()

    if not channels:
        raise NotFoundError("没有找到活跃的渠道")

    results: List[SyncModelsResponse] = []
    total_added = 0
    total_updated = 0

    for channel in channels:
        sync_result = await _sync_channel_models(db, channel)
        results.append(sync_result)
        total_added += sync_result.models_added
        total_updated += sync_result.models_updated

    logger.info(
        f"Models synced by {current_user.username}: "
        f"{total_added} added, {total_updated} updated"
    )

    return ResponseModel(
        code=200,
        message="同步完成",
        data=SyncAllModelsResponse(
            results=results,
            total_added=total_added,
            total_updated=total_updated,
        ),
    )


async def _sync_channel_models(
    db: AsyncSession,
    channel: Channel,
) -> SyncModelsResponse:
    """同步单个渠道的模型.

    Args:
        db: 数据库会话
        channel: 渠道对象

    Returns:
        同步结果
    """
    result = SyncModelsResponse(
        provider=channel.name,
        channel_type=channel.type,
    )

    try:
        config = channel.config
        provider_models = await fetch_models_from_channel(
            channel_type=channel.type,
            api_key=config.get("api_key", ""),
            api_base=config.get("api_base"),
            api_version=config.get("api_version"),
            organization=config.get("organization"),
        )

        result.models_total = len(provider_models)

        for pm in provider_models:
            # 检查模型是否已存在
            existing = await db.execute(
                select(ModelDef).where(ModelDef.id == pm.id)
            )
            existing_model = existing.scalar_one_or_none()

            if existing_model:
                # 更新现有模型
                existing_model.name = pm.name
                existing_model.provider = pm.provider
                existing_model.channel_type = pm.channel_type
                existing_model.context_window = pm.context_window
                existing_model.capabilities = pm.capabilities
                existing_model.status = "active"
                result.models_updated += 1
            else:
                # 创建新模型
                new_model = ModelDef(
                    id=pm.id,
                    name=pm.name,
                    provider=pm.provider,
                    channel_type=pm.channel_type,
                    description=pm.description,
                    capabilities=pm.capabilities or ["chat"],
                    context_window=pm.context_window or 0,
                    pricing_input=0,
                    pricing_output=0,
                    status="active",
                )
                db.add(new_model)
                result.models_added += 1

        await db.commit()

    except Exception as e:
        logger.error(f"Failed to sync models from {channel.name}: {e}")
        result.error = str(e)

    return result


@router.post("/sync/{channel_id}", response_model=ResponseModel[SyncModelsResponse])
async def sync_models_from_single_channel(
    channel_id: int,
    current_user: UserModel = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """从指定渠道同步模型列表.

    Args:
        channel_id: 渠道ID
        current_user: 当前管理员用户
        db: 数据库会话

    Returns:
        同步结果
    """
    result = await db.execute(
        select(Channel).where(Channel.id == channel_id)
    )
    channel = result.scalar_one_or_none()

    if not channel:
        raise NotFoundError("渠道不存在")

    sync_result = await _sync_channel_models(db, channel)

    return ResponseModel(
        code=200,
        message="同步完成",
        data=sync_result,
    )
