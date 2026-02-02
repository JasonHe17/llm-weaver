"""
模型管理接口
提供可用模型列表查询
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.api.deps import get_current_active_user, get_db, get_current_api_key
from app.core.exceptions import NotFoundError
from app.db.models.model_def import ModelDef
from app.db.models.user import User as UserModel
from app.schemas import ResponseModel
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


@router.get("", response_model=ResponseModel[ModelsListResponse])
async def list_models(
    provider: Optional[str] = Query(None, description="供应商筛选"),
    capability: Optional[str] = Query(None, description="能力筛选"),
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """获取可用模型列表.
    
    Args:
        provider: 供应商筛选
        capability: 能力筛选 (chat/vision/function_calling)
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        可用模型列表
    """
    query = select(ModelDef).where(ModelDef.status == "active")
    
    if provider:
        query = query.where(ModelDef.provider == provider)
    
    if capability:
        query = query.where(ModelDef.capabilities.contains([capability]))
    
    result = await db.execute(query)
    models = result.scalars().all()
    
    items = [
        ModelInfo(
            id=m.id,
            name=m.name,
            provider=m.provider,
            capabilities=m.capabilities or [],
            context_window=m.context_window,
            pricing_input=float(m.pricing_input),
            pricing_output=float(m.pricing_output),
            status=m.status,
        )
        for m in models
    ]
    
    return ResponseModel(
        code=200,
        message="success",
        data=ModelsListResponse(items=items, total=len(items)),
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
