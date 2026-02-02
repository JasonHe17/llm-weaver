"""
API依赖注入模块
提供FastAPI依赖项：数据库会话、当前用户、权限验证等
"""

from typing import AsyncGenerator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.logging import logger
from app.core.security import decode_access_token, verify_api_key
from app.db.session import async_session_maker
from app.db.models.user import User
from app.db.models.api_key import APIKey
from sqlalchemy import select

# HTTP Bearer 安全方案
security_bearer = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话.
    
    Yields:
        AsyncSession: 异步数据库会话
    """
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """获取当前认证用户.
    
    Args:
        credentials: HTTP Bearer凭证
        db: 数据库会话
        
    Returns:
        User: 当前用户对象
        
    Raises:
        AuthenticationError: 认证失败
    """
    if not credentials:
        raise AuthenticationError("未提供认证凭证")
    
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if not payload:
        raise AuthenticationError("无效的认证令牌")
    
    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError("令牌中未找到用户信息")
    
    # 查询用户
    result = await db.execute(
        select(User).where(User.id == int(user_id), User.is_active == True)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise AuthenticationError("用户不存在或已被禁用")
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """获取当前活跃用户（状态检查）.
    
    Args:
        current_user: 当前用户
        
    Returns:
        User: 当前活跃用户
        
    Raises:
        AuthorizationError: 用户状态异常
    """
    if current_user.status != "active":
        raise AuthorizationError("用户账户状态异常")
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """获取当前管理员用户.
    
    Args:
        current_user: 当前用户
        
    Returns:
        User: 当前管理员用户
        
    Raises:
        AuthorizationError: 非管理员用户
    """
    if current_user.role != "admin":
        raise AuthorizationError("需要管理员权限")
    return current_user


async def get_current_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: AsyncSession = Depends(get_db),
) -> APIKey:
    """通过API Key获取认证信息.
    
    用于OpenAI兼容接口的认证
    
    Args:
        credentials: HTTP Bearer凭证
        db: 数据库会话
        
    Returns:
        APIKey: API Key对象
        
    Raises:
        AuthenticationError: 认证失败
    """
    if not credentials:
        raise AuthenticationError("未提供API Key")
    
    api_key = credentials.credentials
    
    # API Key格式检查
    if not api_key.startswith("sk-llmweaver-"):
        raise AuthenticationError("无效的API Key格式")
    
    # 查询所有active的API keys进行验证
    result = await db.execute(
        select(APIKey).where(
            APIKey.status == "active",
        )
    )
    api_keys = result.scalars().all()
    
    # 验证API Key
    for key in api_keys:
        if verify_api_key(api_key, key.key_hash):
            # 检查是否过期
            from datetime import datetime, timezone
            if key.expires_at and key.expires_at < datetime.now(timezone.utc):
                raise AuthenticationError("API Key已过期")
            
            return key
    
    raise AuthenticationError("无效的API Key")


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """可选的当前用户获取（用于公共接口）.
    
    Args:
        credentials: HTTP Bearer凭证
        db: 数据库会话
        
    Returns:
        Optional[User]: 当前用户或None
    """
    try:
        return await get_current_user(credentials, db)
    except AuthenticationError:
        return None


class PermissionChecker:
    """权限检查类.
    
    用于检查用户是否拥有指定权限
    
    Example:
        @router.get("/admin-only", dependencies=[Depends(PermissionChecker("admin"))])
        async def admin_only_endpoint():
            ...
    """
    
    def __init__(self, required_role: str = "user"):
        """初始化权限检查器.
        
        Args:
            required_role: 要求的角色 (admin/user)
        """
        self.required_role = required_role
    
    async def __call__(self, user: User = Depends(get_current_active_user)) -> User:
        """检查权限.
        
        Args:
            user: 当前用户
            
        Returns:
            User: 通过权限检查的用户
            
        Raises:
            AuthorizationError: 权限不足
        """
        role_hierarchy = {"user": 1, "admin": 2}
        
        user_level = role_hierarchy.get(user.role, 0)
        required_level = role_hierarchy.get(self.required_role, 1)
        
        if user_level < required_level:
            raise AuthorizationError(f"需要{self.required_role}权限")
        
        return user
