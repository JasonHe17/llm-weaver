"""
通用响应模型
"""

from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ResponseModel(BaseModel, Generic[T]):
    """通用响应模型.
    
    Attributes:
        code: 状态码
        message: 消息
        data: 数据内容
    """
    
    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="消息")
    data: Optional[T] = Field(default=None, description="数据内容")


class PaginationParams(BaseModel):
    """分页参数.
    
    Attributes:
        page: 页码
        page_size: 每页数量
    """
    
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应模型.
    
    Attributes:
        items: 数据列表
        total: 总数量
        page: 当前页码
        page_size: 每页数量
        total_pages: 总页数
    """
    
    items: List[T] = Field(default=[], description="数据列表")
    total: int = Field(default=0, description="总数量")
    page: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=20, description="每页数量")
    total_pages: int = Field(default=0, description="总页数")
    
    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedResponse[T]":
        """创建分页响应.
        
        Args:
            items: 数据列表
            total: 总数量
            page: 当前页码
            page_size: 每页数量
            
        Returns:
            PaginatedResponse: 分页响应对象
        """
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


class ErrorResponse(BaseModel):
    """错误响应模型.
    
    Attributes:
        code: 错误码
        message: 错误消息
        detail: 详细错误信息
    """
    
    code: int = Field(default=500, description="错误码")
    message: str = Field(default="Internal server error", description="错误消息")
    detail: Optional[Any] = Field(default=None, description="详细错误信息")
