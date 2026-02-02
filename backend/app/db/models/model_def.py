"""
模型定义 (支持的AI模型)
"""

from sqlalchemy import String, Numeric, Integer, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, BaseModelMixin


class ModelDef(Base, BaseModelMixin):
    """模型定义."""
    
    __tablename__ = "models"
    
    id: Mapped[str] = mapped_column(String(100), primary_key=True)  # 如: gpt-4
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    channel_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    
    # 模型能力
    capabilities: Mapped[dict] = mapped_column(JSON, default=list)  # [chat, vision, function_calling]
    context_window: Mapped[int] = mapped_column(Integer, nullable=True)
    
    # 定价 (每1K tokens)
    pricing_input: Mapped[float] = mapped_column(Numeric(10, 6), default=0)
    pricing_output: Mapped[float] = mapped_column(Numeric(10, 6), default=0)
    
    # 额外配置
    config: Mapped[dict] = mapped_column(JSON, nullable=True)
    
    # 状态
    status: Mapped[str] = mapped_column(String(20), default="active")
    
    def __repr__(self) -> str:
        return f"<ModelDef {self.id}>"
