"""
API Key 相关模型
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


class APIKeyBase(BaseModel):
    """API Key 基础模型."""
    
    name: Optional[str] = Field(default=None, max_length=100, description="名称")


class APIKeyCreate(APIKeyBase):
    """API Key 创建请求模型.
    
    Attributes:
        budget_limit: 预算限制（0表示无限制）
        rate_limit: 速率限制（每分钟请求数）
        allowed_models: 允许的模型列表
        expires_at: 过期时间
    """
    
    budget_limit: float = Field(default=0, ge=0, description="预算限制")
    rate_limit: int = Field(default=60, ge=1, description="速率限制（每分钟）")
    allowed_models: Optional[List[str]] = Field(default=None, description="允许的模型列表")
    expires_at: Optional[datetime] = Field(default=None, description="过期时间")


class APIKeyCreateResponse(BaseModel):
    """API Key 创建响应模型.
    
    注意：创建时只返回一次完整的API Key
    
    Attributes:
        id: API Key ID
        key: 完整的API Key（仅创建时返回）
        name: 名称
        created_at: 创建时间
    """
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    key: str = Field(..., description="完整的API Key（仅创建时返回）")
    name: Optional[str] = None
    created_at: datetime


class APIKeyUpdate(BaseModel):
    """API Key 更新请求模型."""
    
    name: Optional[str] = Field(default=None, max_length=100)
    status: Optional[str] = Field(default=None, pattern="^(active|inactive|revoked)$")
    budget_limit: Optional[float] = Field(default=None, ge=0)
    rate_limit: Optional[int] = Field(default=None, ge=1)
    allowed_models: Optional[List[str]] = None
    expires_at: Optional[datetime] = None


class APIKeyResponse(BaseModel):
    """API Key 响应模型.
    
    Attributes:
        id: API Key ID
        name: 名称
        key_mask: 遮盖后的API Key
        status: 状态
        budget_limit: 预算限制
        budget_used: 已用预算
        rate_limit: 速率限制
        allowed_models: 允许的模型列表
        expires_at: 过期时间
        last_used_at: 最后使用时间
        created_at: 创建时间
    """
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: Optional[str] = None
    key_mask: str = Field(..., description="遮盖后的API Key")
    status: str
    budget_limit: float
    budget_used: float
    rate_limit: int
    allowed_models: Optional[List[str]] = None
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    created_at: datetime


class APIKeyListResponse(BaseModel):
    """API Key 列表响应模型."""
    
    items: List[APIKeyResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
