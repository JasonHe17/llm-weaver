"""
模型管理接口
提供可用模型列表查询
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.api.deps import get_current_active_user, get_db, get_current_api_key
from app.core.exceptions import NotFoundError
from app.db.models.model_def import ModelDef
from app.db.models.user import User as UserModel
from app.schemas import ResponseModel, PaginatedResponse
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
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """获取所有活跃模型列表（不分页）.
    
    Args:
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        活跃模型列表
    """
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
        message="success",
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
