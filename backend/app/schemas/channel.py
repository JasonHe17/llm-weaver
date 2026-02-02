"""
渠道相关模型
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict


class ModelMappingItem(BaseModel):
    """模型映射项.
    
    Attributes:
        model_id: 模型ID（平台内部）
        mapped_model: 映射的模型名称（供应商侧）
    """
    
    model_id: str = Field(..., description="模型ID")
    mapped_model: str = Field(..., description="映射的模型名称")


class ChannelBase(BaseModel):
    """渠道基础模型."""
    
    name: str = Field(..., min_length=1, max_length=100, description="渠道名称")
    type: str = Field(..., description="渠道类型 (openai/anthropic/azure/gemini)")


class ChannelCreate(ChannelBase):
    """渠道创建请求模型.
    
    Attributes:
        config: 渠道配置（包含API地址、密钥等）
        models: 模型映射列表
        weight: 负载均衡权重
        priority: 优先级
    """
    
    config: Dict[str, Any] = Field(..., description="渠道配置")
    models: List[ModelMappingItem] = Field(default=[], description="模型映射列表")
    weight: int = Field(default=100, ge=0, description="负载均衡权重")
    priority: int = Field(default=0, ge=0, description="优先级")


class ChannelUpdate(BaseModel):
    """渠道更新请求模型."""
    
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    config: Optional[Dict[str, Any]] = None
    models: Optional[List[ModelMappingItem]] = None
    weight: Optional[int] = Field(default=None, ge=0)
    priority: Optional[int] = Field(default=None, ge=0)
    status: Optional[str] = Field(default=None, pattern="^(active|inactive|error)$")


class ChannelResponse(BaseModel):
    """渠道响应模型.
    
    Attributes:
        id: 渠道ID
        name: 名称
        type: 类型
        status: 状态
        weight: 权重
        priority: 优先级
        models: 模型列表
        is_system: 是否系统渠道
        created_at: 创建时间
        updated_at: 更新时间
    """
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    type: str
    status: str
    weight: int
    priority: int
    models: List[ModelMappingItem]
    is_system: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    @classmethod
    def from_orm_with_mappings(cls, channel: Any) -> "ChannelResponse":
        """从ORM对象创建响应模型，包含模型映射.
        
        Args:
            channel: Channel ORM对象
            
        Returns:
            ChannelResponse: 响应模型
        """
        mappings = [
            ModelMappingItem(
                model_id=m.model_id,
                mapped_model=m.mapped_model,
            )
            for m in channel.model_mappings
        ]
        
        return cls(
            id=channel.id,
            name=channel.name,
            type=channel.type,
            status=channel.status,
            weight=channel.weight,
            priority=channel.priority,
            models=mappings,
            is_system=channel.is_system,
            created_at=channel.created_at,
            updated_at=channel.updated_at,
        )


class ChannelListResponse(BaseModel):
    """渠道列表响应模型."""
    
    items: List[ChannelResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ChannelTestResponse(BaseModel):
    """渠道测试响应模型.
    
    Attributes:
        status: 测试状态 (success/error)
        latency_ms: 延迟（毫秒）
        message: 测试消息
        tested_at: 测试时间
    """
    
    status: str = Field(..., description="测试状态")
    latency_ms: int = Field(..., description="延迟（毫秒）")
    message: Optional[str] = Field(default=None, description="测试消息")
    tested_at: datetime = Field(..., description="测试时间")


class ChannelConfig(BaseModel):
    """渠道配置模型.
    
    Attributes:
        api_base: API基础地址
        api_key: API密钥
        api_version: API版本（Azure等需要）
        organization: 组织ID（OpenAI可选）
        timeout: 超时时间（秒）
        max_retries: 最大重试次数
        custom_headers: 自定义请求头
    """
    
    api_base: Optional[str] = Field(default=None, description="API基础地址")
    api_key: str = Field(..., description="API密钥")
    api_version: Optional[str] = Field(default=None, description="API版本")
    organization: Optional[str] = Field(default=None, description="组织ID")
    timeout: int = Field(default=60, description="超时时间（秒）")
    max_retries: int = Field(default=3, description="最大重试次数")
    custom_headers: Optional[Dict[str, str]] = Field(default=None, description="自定义请求头")
