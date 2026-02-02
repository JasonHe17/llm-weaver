"""
认证相关模型
"""

from typing import Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict

from .user import User


class Token(BaseModel):
    """Token模型.
    
    Attributes:
        access_token: 访问令牌
        token_type: 令牌类型
        expires_in: 过期时间（秒）
    """
    
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(default=604800, description="过期时间（秒）")


class TokenPayload(BaseModel):
    """Token载荷模型."""
    
    sub: Optional[str] = None  # 用户ID
    exp: Optional[int] = None  # 过期时间戳
    type: Optional[str] = None  # token类型


class LoginRequest(BaseModel):
    """登录请求模型.
    
    Attributes:
        email: 邮箱
        password: 密码
    """
    
    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., min_length=1, description="密码")


class LoginResponse(BaseModel):
    """登录响应模型.
    
    Attributes:
        access_token: 访问令牌
        token_type: 令牌类型
        expires_in: 过期时间
        user: 用户信息
    """
    
    access_token: str
    token_type: str
    expires_in: int
    user: User


class RegisterRequest(BaseModel):
    """注册请求模型.
    
    Attributes:
        username: 用户名
        email: 邮箱
        password: 密码
    """
    
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., min_length=6, max_length=50, description="密码")


class RefreshTokenRequest(BaseModel):
    """刷新Token请求."""
    
    refresh_token: str = Field(..., description="刷新令牌")


class PasswordResetRequest(BaseModel):
    """密码重置请求."""
    
    email: EmailStr = Field(..., description="邮箱")


class PasswordChangeRequest(BaseModel):
    """密码修改请求."""
    
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=50, description="新密码")
