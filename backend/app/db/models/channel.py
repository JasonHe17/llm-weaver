"""
渠道模型 (上游供应商配置)
"""

from typing import TYPE_CHECKING, List
from sqlalchemy import String, Integer, ForeignKey, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BaseModelMixin

if TYPE_CHECKING:
    from .user import User
    from .model_mapping import ModelMapping


class Channel(Base, BaseModelMixin):
    """渠道模型."""
    
    __tablename__ = "channels"
    
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)  # Null表示系统渠道
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # openai/anthropic/azure/etc
    
    # 配置 (包含API地址、密钥等敏感信息)
    config: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    # 负载均衡配置
    weight: Mapped[int] = mapped_column(Integer, default=100)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    
    # 状态
    status: Mapped[str] = mapped_column(String(20), default="active")
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # 关系
    user: Mapped["User"] = relationship("User")
    model_mappings: Mapped[List["ModelMapping"]] = relationship("ModelMapping", back_populates="channel", lazy="selectin")
    
    def __repr__(self) -> str:
        return f"<Channel {self.name} ({self.type})>"
