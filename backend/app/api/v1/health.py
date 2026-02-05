"""
健康检查接口
"""

import time
from datetime import date, datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func

from app.core.config import settings
from app.core.logging import logger
from app.db.session import get_db
from app.db.models.channel import Channel
from app.db.models.api_key import APIKey
from app.db.models.request_log import RequestLog

router = APIRouter()


@router.get("/health", tags=["health"], summary="基础健康检查")
async def health_check(db: AsyncSession = Depends(get_db)):
    """健康检查端点.

    返回服务基本健康状态，包括数据库连接状态。
    """
    start_time = time.time()
    db_status = "connected"
    db_latency_ms = 0

    try:
        # 检查数据库连接
        result = await db.execute(text("SELECT 1"))
        await result.scalar()
        db_latency_ms = int((time.time() - start_time) * 1000)
    except Exception as e:
        db_status = "disconnected"
        logger.error(f"Database health check failed: {e}")

    return {
        "status": "healthy" if db_status == "connected" else "unhealthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "checks": {
            "database": {
                "status": db_status,
                "latency_ms": db_latency_ms,
            }
        }
    }


@router.get("/health/detailed", tags=["health"], summary="详细健康检查")
async def detailed_health_check(db: AsyncSession = Depends(get_db)):
    """详细健康检查端点.

    返回更详细的系统状态信息，包括各个组件的健康状况。
    """
    checks = {}
    overall_status = "healthy"

    # 检查数据库
    try:
        start_time = time.time()
        await db.execute(text("SELECT 1"))
        db_latency = int((time.time() - start_time) * 1000)
        checks["database"] = {
            "status": "healthy",
            "latency_ms": db_latency,
        }
    except Exception as e:
        checks["database"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        overall_status = "unhealthy"

    # 检查上游供应商连接（可选）
    channel_status = []
    try:
        result = await db.execute(
            select(Channel).where(Channel.status == "active").limit(5)
        )
        channels = result.scalars().all()

        for channel in channels:
            channel_status.append({
                "id": channel.id,
                "name": channel.name,
                "type": channel.type,
                "status": channel.status,
            })

        checks["channels"] = {
            "status": "healthy",
            "active_count": len(channels),
            "channels": channel_status,
        }
    except Exception as e:
        checks["channels"] = {
            "status": "unknown",
            "error": str(e),
        }

    return {
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "checks": checks,
    }


@router.get("/health/metrics", tags=["health"], summary="系统指标")
async def health_metrics(db: AsyncSession = Depends(get_db)):
    """系统指标端点.

    返回系统运行指标，包括请求统计、API Key使用情况等。
    """
    try:
        # 统计API Key数量
        api_key_result = await db.execute(
            select(func.count()).select_from(APIKey)
        )
        total_api_keys = api_key_result.scalar()

        active_api_keys_result = await db.execute(
            select(func.count()).select_from(APIKey).where(APIKey.status == "active")
        )
        active_api_keys = active_api_keys_result.scalar()

        # 统计渠道数量
        channel_result = await db.execute(
            select(func.count()).select_from(Channel)
        )
        total_channels = channel_result.scalar()

        active_channels_result = await db.execute(
            select(func.count()).select_from(Channel).where(Channel.status == "active")
        )
        active_channels = active_channels_result.scalar()

        # 统计今日请求
        from datetime import date, datetime
        today = date.today()
        today_requests_result = await db.execute(
            select(func.count()).select_from(RequestLog).where(
                func.date(RequestLog.created_at) == today
            )
        )
        today_requests = today_requests_result.scalar()

        today_cost_result = await db.execute(
            select(func.coalesce(func.sum(RequestLog.cost), 0)).select_from(RequestLog).where(
                func.date(RequestLog.created_at) == today
            )
        )
        today_cost = float(today_cost_result.scalar() or 0)

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "api_keys": {
                "total": total_api_keys,
                "active": active_api_keys,
            },
            "channels": {
                "total": total_channels,
                "active": active_channels,
            },
            "requests": {
                "today": today_requests,
                "today_cost": round(today_cost, 4),
            }
        }
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e),
        }
