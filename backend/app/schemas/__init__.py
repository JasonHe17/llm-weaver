"""
Pydantic模型（数据验证和序列化）
"""

from .user import User, UserCreate, UserUpdate, UserInDB
from .auth import LoginRequest, LoginResponse, RegisterRequest, Token, TokenPayload
from .api_key import (
    APIKeyCreate,
    APIKeyCreateResponse,
    APIKeyUpdate,
    APIKeyResponse,
    APIKeyListResponse,
)
from .channel import (
    ChannelCreate,
    ChannelUpdate,
    ChannelResponse,
    ChannelListResponse,
    ChannelTestResponse,
)
from .common import ResponseModel, PaginatedResponse, ErrorResponse

__all__ = [
    # 用户
    "User",
    "UserCreate",
    "UserUpdate",
    "UserInDB",
    # 认证
    "LoginRequest",
    "LoginResponse",
    "RegisterRequest",
    "Token",
    "TokenPayload",
    # API Key
    "APIKeyCreate",
    "APIKeyCreateResponse",
    "APIKeyUpdate",
    "APIKeyResponse",
    "APIKeyListResponse",
    # 渠道
    "ChannelCreate",
    "ChannelUpdate",
    "ChannelResponse",
    "ChannelListResponse",
    "ChannelTestResponse",
    # 通用
    "ResponseModel",
    "PaginatedResponse",
    "ErrorResponse",
]
