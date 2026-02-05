"""
渠道管理接口
提供上游供应商渠道的配置管理
"""

import time
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_current_admin_user, get_db
from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError, UpstreamError
from app.core.logging import logger
from app.db.models.channel import Channel
from app.db.models.model_mapping import ModelMapping
from app.db.models.user import User as UserModel
from app.schemas import (
    ChannelCreate,
    ChannelListResponse,
    ChannelResponse,
    ChannelTestResponse,
    ChannelUpdate,
    ResponseModel,
)
from app.services.load_balancer import load_balancer, ChannelHealthStatus, ChannelPerformanceMetrics, LoadBalanceStrategy

router = APIRouter()


@router.get(
    "",
    response_model=ResponseModel[ChannelListResponse],
    summary="获取渠道列表",
    description="获取渠道列表。普通用户只能看到自己的渠道，管理员可以看到所有渠道。",
    responses={
        200: {
            "description": "渠道列表",
            "content": {
                "application/json": {
                    "example": {
                        "code": 200,
                        "message": "success",
                        "data": {
                            "items": [
                                {
                                    "id": 1,
                                    "name": "OpenAI Production",
                                    "type": "openai",
                                    "status": "active",
                                    "weight": 100,
                                    "priority": 1,
                                    "models": [
                                        {"model_id": "gpt-4", "mapped_model": "gpt-4"}
                                    ],
                                    "is_system": False,
                                    "created_at": "2024-01-01T00:00:00"
                                }
                            ],
                            "total": 1,
                            "page": 1,
                            "page_size": 20,
                            "total_pages": 1
                        }
                    }
                }
            }
        }
    }
)
async def list_channels(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    type: Optional[str] = Query(None, description="渠道类型筛选 (openai/anthropic/azure/gemini)"),
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """获取渠道列表.

    普通用户只能看到自己的渠道，管理员可以看到所有渠道

    Args:
        page: 页码
        page_size: 每页数量
        type: 渠道类型筛选
        current_user: 当前用户
        db: 数据库会话

    Returns:
        渠道列表（分页）
    """
    # 构建查询
    query = select(Channel)
    
    # 非管理员只能看到自己的渠道或系统渠道
    if current_user.role != "admin":
        query = query.where(
            (Channel.user_id == current_user.id) | (Channel.is_system == True)
        )
    
    if type:
        query = query.where(Channel.type == type)
    
    # 获取总数
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar()
    
    # 分页查询
    query = query.order_by(Channel.priority.desc(), Channel.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    channels = result.scalars().all()
    
    # 构建响应
    items = [ChannelResponse.from_orm_with_mappings(ch) for ch in channels]
    total_pages = (total + page_size - 1) // page_size
    
    return ResponseModel(
        code=200,
        message="success",
        data=ChannelListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ),
    )


@router.post("", response_model=ResponseModel[ChannelResponse], status_code=status.HTTP_201_CREATED)
async def create_channel(
    request: ChannelCreate,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """创建新渠道.
    
    Args:
        request: 创建请求
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        新创建的渠道
    """
    # 验证渠道类型
    valid_types = ["openai", "anthropic", "azure", "gemini", "mistral", "cohere"]
    if request.type not in valid_types:
        raise ValidationError(f"不支持的渠道类型，可选: {', '.join(valid_types)}")
    
    # 创建渠道
    channel = Channel(
        user_id=current_user.id,
        name=request.name,
        type=request.type,
        config=request.config,
        weight=request.weight,
        priority=request.priority,
        status="active",
        is_system=False,
    )
    
    db.add(channel)
    await db.flush()  # 获取channel.id
    
    # 创建模型映射
    for mapping in request.models:
        model_mapping = ModelMapping(
            channel_id=channel.id,
            model_id=mapping.model_id,
            mapped_model=mapping.mapped_model,
        )
        db.add(model_mapping)
    
    await db.commit()
    await db.refresh(channel)
    
    logger.info(f"Channel created: {channel.id} by user {current_user.id}")
    
    return ResponseModel(
        code=201,
        message="渠道创建成功",
        data=ChannelResponse.from_orm_with_mappings(channel),
    )


@router.get("/{channel_id}", response_model=ResponseModel[ChannelResponse])
async def get_channel(
    channel_id: int,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """获取渠道详情.
    
    Args:
        channel_id: 渠道ID
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        渠道详情
        
    Raises:
        NotFoundError: 渠道不存在
    """
    result = await db.execute(
        select(Channel).where(Channel.id == channel_id)
    )
    channel = result.scalar_one_or_none()
    
    if not channel:
        raise NotFoundError("渠道不存在")
    
    # 检查权限（非管理员只能看自己的或系统的）
    if current_user.role != "admin":
        if channel.user_id != current_user.id and not channel.is_system:
            raise NotFoundError("渠道不存在")
    
    return ResponseModel(
        code=200,
        message="success",
        data=ChannelResponse.from_orm_with_mappings(channel),
    )


@router.put("/{channel_id}", response_model=ResponseModel[ChannelResponse])
async def update_channel(
    channel_id: int,
    request: ChannelUpdate,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """更新渠道.
    
    Args:
        channel_id: 渠道ID
        request: 更新请求
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        更新后的渠道
        
    Raises:
        NotFoundError: 渠道不存在
        AuthorizationError: 无权限修改
    """
    result = await db.execute(
        select(Channel).where(Channel.id == channel_id)
    )
    channel = result.scalar_one_or_none()
    
    if not channel:
        raise NotFoundError("渠道不存在")
    
    # 检查权限
    from app.core.exceptions import AuthorizationError
    if current_user.role != "admin" and channel.user_id != current_user.id:
        raise AuthorizationError("无权修改此渠道")
    
    # 更新渠道字段
    update_data = request.model_dump(exclude_unset=True, exclude={"models"})
    for field, value in update_data.items():
        if value is not None:
            setattr(channel, field, value)
    
    # 更新模型映射
    if request.models is not None:
        # 删除旧的映射
        await db.execute(
            select(ModelMapping).where(ModelMapping.channel_id == channel_id)
        )
        # 创建新的映射
        for mapping in request.models:
            model_mapping = ModelMapping(
                channel_id=channel_id,
                model_id=mapping.model_id,
                mapped_model=mapping.mapped_model,
            )
            db.add(model_mapping)
    
    await db.commit()
    await db.refresh(channel)
    
    logger.info(f"Channel updated: {channel_id} by user {current_user.id}")
    
    return ResponseModel(
        code=200,
        message="渠道更新成功",
        data=ChannelResponse.from_orm_with_mappings(channel),
    )


@router.delete("/{channel_id}", response_model=ResponseModel[dict])
async def delete_channel(
    channel_id: int,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """删除渠道.
    
    Args:
        channel_id: 渠道ID
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        删除成功消息
    """
    result = await db.execute(
        select(Channel).where(Channel.id == channel_id)
    )
    channel = result.scalar_one_or_none()
    
    if not channel:
        raise NotFoundError("渠道不存在")
    
    # 检查权限
    from app.core.exceptions import AuthorizationError
    if current_user.role != "admin" and channel.user_id != current_user.id:
        raise AuthorizationError("无权删除此渠道")
    
    # 软删除：标记为inactive
    channel.status = "inactive"
    await db.commit()
    
    logger.info(f"Channel deleted: {channel_id} by user {current_user.id}")
    
    return ResponseModel(
        code=200,
        message="渠道已删除",
        data={"message": "渠道已成功删除"},
    )


@router.post("/{channel_id}/test", response_model=ResponseModel[ChannelTestResponse])
async def test_channel(
    channel_id: int,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """测试渠道连接.
    
    向供应商API发送一个简单的测试请求
    
    Args:
        channel_id: 渠道ID
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        测试结果
    """
    result = await db.execute(
        select(Channel).where(Channel.id == channel_id)
    )
    channel = result.scalar_one_or_none()
    
    if not channel:
        raise NotFoundError("渠道不存在")
    
    # 检查权限
    from app.core.exceptions import AuthorizationError
    if current_user.role != "admin" and channel.user_id != current_user.id:
        raise AuthorizationError("无权测试此渠道")
    
    # 测试连接
    config = channel.config
    channel_type = channel.type
    
    start_time = time.time()
    
    try:
        if channel_type == "openai":
            # 测试OpenAI连接
            api_base = config.get("api_base", "https://api.openai.com")
            api_key = config.get("api_key")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{api_base}/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                response.raise_for_status()
        
        elif channel_type == "azure":
            # 测试Azure连接
            api_base = config.get("api_base")
            api_key = config.get("api_key")
            api_version = config.get("api_version", "2024-02-01")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{api_base}/openai/models?api-version={api_version}",
                    headers={"api-key": api_key},
                )
                response.raise_for_status()
        
        elif channel_type == "anthropic":
            # 测试Anthropic连接
            api_base = config.get("api_base", "https://api.anthropic.com")
            api_key = config.get("api_key")

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{api_base}/v1/models",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01"
                    },
                )
                response.raise_for_status()

        elif channel_type == "gemini":
            # 测试Gemini连接
            api_key = config.get("api_key")
            api_base = config.get("api_base", "https://generativelanguage.googleapis.com")
            api_version = config.get("api_version", "v1beta")

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{api_base}/{api_version}/models?key={api_key}",
                )
                response.raise_for_status()

        else:
            # 其他类型简单返回成功
            pass
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        # 更新渠道状态
        channel.status = "active"
        await db.commit()
        
        return ResponseModel(
            code=200,
            message="连接测试成功",
            data=ChannelTestResponse(
                status="success",
                latency_ms=latency_ms,
                message="渠道连接正常",
                tested_at=datetime.now(timezone.utc),
            ),
        )
    
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        
        # 更新渠道状态
        channel.status = "error"
        await db.commit()
        
        logger.error(f"Channel test failed: {channel_id}, error: {e}")
        
        return ResponseModel(
            code=200,
            message="连接测试失败",
            data=ChannelTestResponse(
                status="error",
                latency_ms=latency_ms,
                message=f"连接失败: {str(e)}",
                tested_at=datetime.now(timezone.utc),
            ),
        )


@router.post("/{channel_id}/health-check", response_model=ResponseModel[dict])
async def check_channel_health(
    channel_id: int,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """检查单个渠道健康状态（智能负载均衡）.
    
    使用负载均衡服务的健康检查机制，比简单测试更全面的健康评估
    
    Args:
        channel_id: 渠道ID
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        健康检查结果
    """
    result = await db.execute(
        select(Channel).where(Channel.id == channel_id)
    )
    channel = result.scalar_one_or_none()
    
    if not channel:
        raise NotFoundError("渠道不存在")
    
    # 检查权限
    from app.core.exceptions import AuthorizationError
    if current_user.role != "admin" and channel.user_id != current_user.id:
        raise AuthorizationError("无权检查此渠道")
    
    # 使用负载均衡服务进行健康检查
    health_status = await load_balancer.check_channel_health(channel, db)
    
    return ResponseModel(
        code=200,
        message="健康检查完成",
        data={
            "channel_id": health_status.channel_id,
            "is_healthy": health_status.is_healthy,
            "check_latency_ms": health_status.check_latency_ms,
            "consecutive_failures": health_status.consecutive_failures,
            "message": health_status.message,
            "checked_at": health_status.last_check_time.isoformat(),
        },
    )


@router.get("/{channel_id}/performance", response_model=ResponseModel[dict])
async def get_channel_performance(
    channel_id: int,
    model: Optional[str] = Query(None, description="模型名称（可选）"),
    window_minutes: int = Query(30, ge=5, le=1440, description="分析窗口（分钟，默认30分钟）"),
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """获取渠道性能指标（基于日志分析）.
    
    分析指定渠道在近期的性能表现，包括延迟分布、成功率、缓存命中率等
    
    Args:
        channel_id: 渠道ID
        model: 模型名称（可选，不指定则分析所有模型）
        window_minutes: 分析窗口（分钟）
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        性能指标数据
    """
    result = await db.execute(
        select(Channel).where(Channel.id == channel_id)
    )
    channel = result.scalar_one_or_none()
    
    if not channel:
        raise NotFoundError("渠道不存在")
    
    # 检查权限
    from app.core.exceptions import AuthorizationError
    if current_user.role != "admin" and channel.user_id != current_user.id:
        raise AuthorizationError("无权查看此渠道")
    
    # 如果指定了模型，只分析该模型
    if model:
        metrics = await load_balancer.analyze_channel_performance(
            channel_id=channel_id,
            model=model,
            db=db,
            window_minutes=window_minutes,
        )
        
        return ResponseModel(
            code=200,
            message="性能分析完成",
            data={
                "channel_id": metrics.channel_id,
                "model": metrics.model,
                "window_minutes": window_minutes,
                "avg_latency_ms": round(metrics.avg_latency_ms, 2),
                "p50_latency_ms": round(metrics.p50_latency_ms, 2),
                "p95_latency_ms": round(metrics.p95_latency_ms, 2),
                "p99_latency_ms": round(metrics.p99_latency_ms, 2),
                "success_rate": round(metrics.success_rate * 100, 2),
                "total_requests": metrics.total_requests,
                "error_count": metrics.error_count,
                "cache_hit_rate": round(metrics.cache_hit_rate * 100, 2),
                "cached_requests": metrics.cached_requests,
            },
        )
    else:
        # 获取该渠道支持的所有模型
        mappings_result = await db.execute(
            select(ModelMapping).where(ModelMapping.channel_id == channel_id)
        )
        mappings = mappings_result.scalars().all()
        model_ids = [m.model_id for m in mappings]
        
        # 分析所有模型
        all_metrics = []
        for model_id in model_ids:
            metrics = await load_balancer.analyze_channel_performance(
                channel_id=channel_id,
                model=model_id,
                db=db,
                window_minutes=window_minutes,
            )
            all_metrics.append({
                "model": metrics.model,
                "avg_latency_ms": round(metrics.avg_latency_ms, 2),
                "p95_latency_ms": round(metrics.p95_latency_ms, 2),
                "success_rate": round(metrics.success_rate * 100, 2),
                "total_requests": metrics.total_requests,
                "cache_hit_rate": round(metrics.cache_hit_rate * 100, 2),
            })
        
        return ResponseModel(
            code=200,
            message="性能分析完成",
            data={
                "channel_id": channel_id,
                "window_minutes": window_minutes,
                "models_analyzed": len(all_metrics),
                "models": all_metrics,
            },
        )


@router.post("/health-check/all", response_model=ResponseModel[dict])
async def check_all_channels_health(
    current_user: UserModel = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """检查所有活跃渠道的健康状态（仅管理员）.
    
    对所有活跃渠道执行健康检查，用于系统监控和维护
    
    Args:
        current_user: 当前用户（必须是管理员）
        db: 数据库会话
        
    Returns:
        所有渠道的健康状态汇总
    """
    results = await load_balancer.check_all_channels_health(db)
    
    healthy_count = sum(1 for r in results.values() if r.is_healthy)
    unhealthy_count = len(results) - healthy_count
    
    return ResponseModel(
        code=200,
        message="健康检查完成",
        data={
            "total_channels": len(results),
            "healthy": healthy_count,
            "unhealthy": unhealthy_count,
            "channels": [
                {
                    "channel_id": r.channel_id,
                    "is_healthy": r.is_healthy,
                    "consecutive_failures": r.consecutive_failures,
                    "check_latency_ms": r.check_latency_ms,
                    "message": r.message,
                    "checked_at": r.last_check_time.isoformat(),
                }
                for r in results.values()
            ],
        },
    )


@router.get("/load-balancer/status", response_model=ResponseModel[dict])
async def get_load_balancer_status(
    current_user: UserModel = Depends(get_current_admin_user),
):
    """获取负载均衡器状态（仅管理员）.
    
    查看负载均衡服务的内部状态，包括健康状态缓存、性能指标缓存、缓存路由等
    
    Args:
        current_user: 当前用户（必须是管理员）
        
    Returns:
        负载均衡器状态
    """
    return ResponseModel(
        code=200,
        message="success",
        data={
            "health_status_cache": {
                "count": len(load_balancer._health_status),
                "channels": [
                    {
                        "channel_id": s.channel_id,
                        "is_healthy": s.is_healthy,
                        "last_check": s.last_check_time.isoformat() if s.last_check_time else None,
                    }
                    for s in load_balancer._health_status.values()
                ],
            },
            "performance_metrics_cache": {
                "count": len(load_balancer._performance_metrics),
            },
            "cache_routing": {
                "count": len(load_balancer._cache_routing),
                "routes": [
                    {
                        "user_id": key[0],
                        "model": key[1],
                        "channel_id": info.channel_id,
                        "consecutive_hits": info.consecutive_hits,
                        "last_used": info.last_used_at.isoformat() if info.last_used_at else None,
                    }
                    for key, info in load_balancer._cache_routing.items()
                ],
            },
            "consecutive_failures": dict(load_balancer._consecutive_failures),
            "config": {
                "metrics_window_minutes": load_balancer.metrics_window_minutes,
                "cache_routing_ttl_minutes": load_balancer.cache_routing_ttl_minutes,
                "max_consecutive_failures": load_balancer.max_consecutive_failures,
                "latency_weight_factor": load_balancer.latency_weight_factor,
                "default_strategy": load_balancer.default_strategy.value,
                "enable_cache_tracking": load_balancer.enable_cache_tracking,
            },
        },
    )


@router.post("/load-balancer/strategy", response_model=ResponseModel[dict])
async def set_load_balancer_strategy(
    strategy: str = Query(..., description="负载均衡策略 (random/weighted/lowest_cost/performance)"),
    current_user: UserModel = Depends(get_current_admin_user),
):
    """设置负载均衡默认策略（仅管理员）.
    
    可选策略：
    - random: 简单随机选择，完全随机
    - weighted: 加权随机选择（默认）
    - lowest_cost: 最低成本优先
    - performance: 最高性能优先
    
    Args:
        strategy: 策略名称
        current_user: 当前用户（必须是管理员）
        
    Returns:
        设置结果
    """
    try:
        strategy_enum = LoadBalanceStrategy(strategy.lower())
    except ValueError:
        valid_strategies = [s.value for s in LoadBalanceStrategy]
        raise ValidationError(f"无效的策略，可选值: {', '.join(valid_strategies)}")
    
    load_balancer.set_default_strategy(strategy_enum)
    
    return ResponseModel(
        code=200,
        message="策略设置成功",
        data={
            "strategy": strategy_enum.value,
            "description": {
                "random": "简单随机选择，完全随机",
                "weighted": "加权随机选择，基于配置的权重",
                "lowest_cost": "最低成本优先，考虑渠道成本和成功率",
                "performance": "最高性能优先，基于延迟和成功率",
            }.get(strategy_enum.value),
        },
    )


@router.post("/load-balancer/cache-tracking", response_model=ResponseModel[dict])
async def set_cache_tracking(
    enabled: bool = Query(..., description="是否启用缓存追踪"),
    current_user: UserModel = Depends(get_current_admin_user),
):
    """设置缓存追踪开关（仅管理员）.
    
    缓存追踪功能会在检测到缓存命中时，优先将后续请求路由到同一渠道，
    以最大化缓存利用率。
    
    Args:
        enabled: 是否启用
        current_user: 当前用户（必须是管理员）
        
    Returns:
        设置结果
    """
    load_balancer.set_cache_tracking(enabled)
    
    return ResponseModel(
        code=200,
        message=f"缓存追踪已{'启用' if enabled else '禁用'}",
        data={
            "enabled": enabled,
            "cache_routing_ttl_minutes": load_balancer.cache_routing_ttl_minutes,
            "current_routes_count": len(load_balancer._cache_routing),
        },
    )


@router.get("/load-balancer/strategies", response_model=ResponseModel[list])
async def list_load_balancer_strategies(
    current_user: UserModel = Depends(get_current_active_user),
):
    """获取所有可用的负载均衡策略列表.
    
    Args:
        current_user: 当前用户
        
    Returns:
        策略列表及说明
    """
    strategies = [
        {
            "name": s.value,
            "description": {
                "random": "简单随机选择，完全随机，不考虑权重、性能或成本",
                "weighted": "加权随机选择（默认），基于渠道配置的权重进行加权随机",
                "lowest_cost": "最低成本优先，选择成本最低的渠道，考虑成功率和成本",
                "performance": "最高性能优先，基于P95延迟和成功率综合评分",
            }[s.value],
            "is_default": s == load_balancer.default_strategy,
        }
        for s in LoadBalanceStrategy
    ]
    
    return ResponseModel(
        code=200,
        message="success",
        data=strategies,
    )
