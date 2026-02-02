"""
API Key模型
"""

from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, Numeric, Integer, ForeignKey, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BaseModelMixin

if TYPE_CHECKING:
    from .user import User


class APIKey(Base, BaseModelMixin):
    """API Key模型."""
    
    __tablename__ = "api_keys"
    
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active/inactive/revoked
    
    # 预算控制
    budget_limit: Mapped[float] = mapped_column(Numeric(15, 4), default=0)  # 0表示无限制
    budget_used: Mapped[float] = mapped_column(Numeric(15, 4), default=0)
    rate_limit: Mapped[int] = mapped_column(Integer, default=60)  # 每分钟请求数
    
    # 限制配置
    allowed_models: Mapped[dict] = mapped_column(JSON, nullable=True)  # 允许的模型列表
    ip_whitelist: Mapped[dict] = mapped_column(JSON, nullable=True)  # IP白名单
    
    # 时间戳
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # 关系
    user: Mapped["User"] = relationship("User", back_populates="api_keys")
    
    def __repr__(self) -> str:
        return f"<APIKey {self.name}>"
