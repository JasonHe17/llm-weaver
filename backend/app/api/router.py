"""
API路由聚合
"""

from fastapi import APIRouter

from app.api.v1 import auth, api_keys, channels, models, usage, health

# 创建主路由
api_router = APIRouter()

# 注册各模块路由
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(api_keys.router, prefix="/api-keys", tags=["api-keys"])
api_router.include_router(channels.router, prefix="/channels", tags=["channels"])
api_router.include_router(models.router, prefix="/models", tags=["models"])
api_router.include_router(usage.router, prefix="/usage", tags=["usage"])
