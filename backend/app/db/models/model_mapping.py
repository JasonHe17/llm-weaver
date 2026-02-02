"""
模型映射 (渠道与模型的关系)
"""

from typing import TYPE_CHECKING
from sqlalchemy import String, ForeignKey, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BaseModelMixin

if TYPE_CHECKING:
    from .channel import Channel


class ModelMapping(Base, BaseModelMixin):
    """模型映射."""
    
    __tablename__ = "model_mappings"
    
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id"), nullable=False)
    model_id: Mapped[str] = mapped_column(String(100), ForeignKey("models.id"), nullable=False)
    
    # 映射后的模型名称
    mapped_model: Mapped[str] = mapped_column(String(100), nullable=True)
    
    # 配置覆盖
    config_override: Mapped[dict] = mapped_column(JSON, nullable=True)
    
    # 是否启用
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # 关系
    channel: Mapped["Channel"] = relationship("Channel", back_populates="model_mappings")
    
    def __repr__(self) -> str:
        return f"<ModelMapping {self.model_id} -> {self.mapped_model}>"
