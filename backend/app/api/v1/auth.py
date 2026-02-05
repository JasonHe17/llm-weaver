"""
认证相关接口
提供用户登录、注册、Token刷新等功能
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_active_user
from app.core.config import settings
from app.core.exceptions import AuthenticationError, BusinessError, ValidationError
from app.core.logging import logger
from app.core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
)
from app.db.models.user import User
from app.schemas import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    ResponseModel,
    Token,
    User,
)

router = APIRouter()


@router.post(
    "/login",
    response_model=ResponseModel[LoginResponse],
    summary="用户登录",
    description="使用邮箱和密码进行认证，返回JWT访问令牌",
    responses={
        200: {
            "description": "登录成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "登录成功",
                        "data": {
                            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "token_type": "bearer",
                            "expires_in": 604800,
                            "user": {
                                "id": 1,
                                "username": "admin",
                                "email": "admin@example.com",
                                "role": "admin",
                                "status": "active",
                                "created_at": "2024-01-01T00:00:00",
                            },
                        },
                    }
                }
            },
        },
        401: {
            "description": "认证失败",
            "content": {
                "application/json": {
                    "example": {
                        "code": 401,
                        "message": "邮箱或密码错误",
                        "data": None,
                    }
                }
            },
        },
    },
)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """用户登录.
    
    使用邮箱和密码进行认证，返回JWT访问令牌
    
    Args:
        request: 登录请求
        db: 数据库会话
        
    Returns:
        包含访问令牌和用户信息
        
    Raises:
        AuthenticationError: 认证失败
    """
    # 查询用户
    result = await db.execute(
        select(User).where(User.email == request.email, User.is_active == True)
    )
    user = result.scalar_one_or_none()
    
    # 验证用户存在且密码正确
    if not user or not verify_password(request.password, user.password_hash):
        logger.warning(f"Login failed for email: {request.email}")
        raise AuthenticationError("邮箱或密码错误")
    
    # 检查用户状态
    if user.status != "active":
        logger.warning(f"Login attempt for inactive user: {user.id}")
        raise AuthenticationError("账户已被禁用")
    
    # 创建访问令牌
    access_token = create_access_token(
        subject=user.id,
        extra_claims={
            "role": user.role,
            "email": user.email,
        },
    )
    
    logger.info(f"User logged in successfully: {user.id}")
    
    return ResponseModel(
        code=200,
        message="登录成功",
        data=LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=User.model_validate(user),
        ),
    )


@router.post(
    "/register",
    response_model=ResponseModel[User],
    status_code=status.HTTP_201_CREATED,
    summary="用户注册",
    description="创建新用户账户",
    responses={
        201: {
            "description": "注册成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 201,
                        "message": "注册成功",
                        "data": {
                            "id": 1,
                            "username": "johndoe",
                            "email": "john@example.com",
                            "role": "user",
                            "status": "active",
                            "created_at": "2024-01-01T00:00:00",
                        },
                    }
                }
            },
        },
        400: {
            "description": "验证错误",
            "content": {
                "application/json": {
                    "example": {
                        "code": 400,
                        "message": "该邮箱已被注册",
                        "data": None,
                    }
                }
            },
        },
    },
)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """用户注册.

    创建新用户账户

    Args:
        request: 注册请求
        db: 数据库会话

    Returns:
        新创建的用户信息

    Raises:
        ValidationError: 邮箱或用户名已存在
    """
    # 检查邮箱是否已存在
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        raise ValidationError("该邮箱已被注册")
    
    # 检查用户名是否已存在
    result = await db.execute(select(User).where(User.username == request.username))
    if result.scalar_one_or_none():
        raise ValidationError("该用户名已被使用")
    
    # 创建新用户
    new_user = User(
        username=request.username,
        email=request.email,
        password_hash=get_password_hash(request.password),
        role="user",
        status="active",
        is_active=True,
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    logger.info(f"New user registered: {new_user.id} ({new_user.email})")
    
    return ResponseModel(
        code=201,
        message="注册成功",
        data=User.model_validate(new_user),
    )


@router.post("/refresh", response_model=ResponseModel[Token])
async def refresh_token(
    current_user: User = Depends(get_current_active_user),
):
    """刷新访问令牌.
    
    使用当前有效的令牌获取新的访问令牌
    
    Args:
        current_user: 当前登录用户
        
    Returns:
        新的访问令牌
    """
    # 创建新的访问令牌
    access_token = create_access_token(
        subject=current_user.id,
        extra_claims={
            "role": current_user.role,
            "email": current_user.email,
        },
    )
    
    logger.info(f"Token refreshed for user: {current_user.id}")
    
    return ResponseModel(
        code=200,
        message="刷新成功",
        data=Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        ),
    )


@router.get("/me", response_model=ResponseModel[User])
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
):
    """获取当前登录用户信息.
    
    Args:
        current_user: 当前登录用户
        
    Returns:
        当前用户信息
    """
    return ResponseModel(
        code=200,
        message="success",
        data=User.model_validate(current_user),
    )


@router.post("/logout", response_model=ResponseModel[dict])
async def logout(
    current_user: User = Depends(get_current_active_user),
):
    """用户登出.
    
    客户端应删除本地存储的令牌
    
    Args:
        current_user: 当前登录用户
        
    Returns:
        登出成功消息
    """
    logger.info(f"User logged out: {current_user.id}")
    
    # 注意：JWT 是无状态的，服务器端无法真正"注销"令牌
    # 如果需要支持令牌撤销，需要将令牌加入黑名单（Redis等）
    
    return ResponseModel(
        code=200,
        message="登出成功",
        data={"message": "已成功登出，请清除本地令牌"},
    )


@router.post("/change-password", response_model=ResponseModel[dict])
async def change_password(
    old_password: str,
    new_password: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """修改密码.
    
    Args:
        old_password: 旧密码
        new_password: 新密码
        current_user: 当前登录用户
        db: 数据库会话
        
    Returns:
        修改成功消息
        
    Raises:
        AuthenticationError: 旧密码错误
        ValidationError: 新密码不符合要求
    """
    # 验证旧密码
    if not verify_password(old_password, current_user.password_hash):
        raise AuthenticationError("旧密码错误")
    
    # 验证新密码
    if len(new_password) < 6:
        raise ValidationError("新密码至少需要6位字符")
    
    if old_password == new_password:
        raise ValidationError("新密码不能与旧密码相同")
    
    # 更新密码
    current_user.password_hash = get_password_hash(new_password)
    await db.commit()
    
    logger.info(f"Password changed for user: {current_user.id}")
    
    return ResponseModel(
        code=200,
        message="密码修改成功",
        data={"message": "密码已更新，请使用新密码重新登录"},
    )
