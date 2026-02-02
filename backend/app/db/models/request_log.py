"""
请求日志模型
"""

from datetime import datetime
from sqlalchemy import (
    String,
    Integer,
    Numeric,
    ForeignKey,
    DateTime,
    JSON,
    Text,
    INET,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, BaseModelMixin


class RequestLog(Base, BaseModelMixin):
    """请求日志."""
    
    __tablename__ = "request_logs"
    
    # 请求标识
    request_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    
    # 关联信息
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    api_key_id: Mapped[int] = mapped_column(ForeignKey("api_keys.id"), nullable=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id"), nullable=True)
    
    # 请求信息
    model: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    mapped_model: Mapped[str] = mapped_column(String(100), nullable=True)
    
    # HTTP信息
    request_method: Mapped[str] = mapped_column(String(10), nullable=True)
    request_path: Mapped[str] = mapped_column(String(500), nullable=True)
    request_headers: Mapped[dict] = mapped_column(JSON, nullable=True)
    request_body: Mapped[dict] = mapped_column(JSON, nullable=True)
    
    # 响应信息
    response_status: Mapped[int] = mapped_column(Integer, nullable=True)
    response_body: Mapped[dict] = mapped_column(JSON, nullable=True)
    
    # Token和费用
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost: Mapped[float] = mapped_column(Numeric(15, 6), default=0)
    
    # 性能
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    
    # 状态
    status: Mapped[str] = mapped_column(String(20), nullable=True, index=True)  # success/error/timeout
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    
    # 客户端信息
    client_ip: Mapped[str] = mapped_column(INET, nullable=True)
    
    def __repr__(self) -> str:
        return f"<RequestLog {self.request_id}>"
