"""
用户相关模型
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserBase(BaseModel):
    """用户基础模型."""
    
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱")


class UserCreate(UserBase):
    """用户创建模型.
    
    Attributes:
        password: 密码（6-50位）
    """
    
    password: str = Field(..., min_length=6, max_length=50, description="密码")


class UserUpdate(BaseModel):
    """用户更新模型."""
    
    username: Optional[str] = Field(default=None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=6, max_length=50)
    is_active: Optional[bool] = None


class UserInDB(UserBase):
    """数据库中的用户模型（包含敏感信息）."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    role: str
    status: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class User(UserBase):
    """用户响应模型（返回给客户端）."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    role: str = Field(default="user", description="角色")
    status: str = Field(default="active", description="状态")
    created_at: datetime
    updated_at: Optional[datetime] = None


class UserProfile(BaseModel):
    """用户个人资料."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    username: str
    email: str
    role: str
    created_at: datetime
    api_key_count: int = Field(default=0, description="API Key数量")
