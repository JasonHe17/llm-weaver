"""
用量统计模型
"""

from datetime import date
from sqlalchemy import Date, Integer, BigInteger, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, BaseModelMixin


class UsageStats(Base, BaseModelMixin):
    """用量统计."""
    
    __tablename__ = "usage_stats"
    
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    api_key_id: Mapped[int] = mapped_column(ForeignKey("api_keys.id"), nullable=True)
    
    # 时间
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    hour: Mapped[int] = mapped_column(Integer, nullable=True)  # 可选,按小时统计
    
    # 统计数据
    request_count: Mapped[int] = mapped_column(Integer, default=0)
    prompt_tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    completion_tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    total_tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    total_cost: Mapped[float] = mapped_column(Numeric(15, 4), default=0)
    
    def __repr__(self) -> str:
        return f"<UsageStats {self.date}>"
