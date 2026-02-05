"""
智能负载均衡服务
提供多种负载均衡策略：随机选择、最低成本、最高性能
支持健康检查、延迟分析、可选的缓存感知路由
"""

import asyncio
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
from enum import Enum
import statistics

import httpx
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.db.models.channel import Channel
from app.db.models.model_mapping import ModelMapping
from app.db.models.request_log import RequestLog


class LoadBalanceStrategy(str, Enum):
    """负载均衡策略枚举."""
    
    RANDOM = "random"              # 简单随机选择
    WEIGHTED_RANDOM = "weighted"   # 加权随机（默认）
    LOWEST_COST = "lowest_cost"    # 最低成本优先
    BEST_PERFORMANCE = "performance"  # 最高性能优先


@dataclass
class ChannelHealthStatus:
    """渠道健康状态."""
    
    channel_id: int
    is_healthy: bool
    last_check_time: datetime
    consecutive_failures: int = 0
    average_latency_ms: float = 0.0
    error_rate: float = 0.0
    check_latency_ms: int = 0
    message: Optional[str] = None


@dataclass
class ChannelPerformanceMetrics:
    """渠道性能指标（基于日志分析）."""
    
    channel_id: int
    model: str
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    success_rate: float = 1.0
    total_requests: int = 0
    error_count: int = 0
    cached_requests: int = 0
    cache_hit_rate: float = 0.0
    calculated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CacheRoutingInfo:
    """缓存路由信息（用于sticky routing）."""
    
    channel_id: int
    model: str
    has_cache_enabled: bool
    last_used_at: datetime
    consecutive_hits: int = 0


@dataclass
class ChannelCostInfo:
    """渠道成本信息."""
    
    channel_id: int
    model: str
    input_cost_per_1k: float  # 每1K输入token成本
    output_cost_per_1k: float  # 每1K输出token成本
    
    @property
    def average_cost_per_request(self) -> float:
        """估算每次请求的平均成本（假设输入输出各占50%）."""
        return (self.input_cost_per_1k + self.output_cost_per_1k) / 2


class LoadBalancerService:
    """智能负载均衡服务.
    
    支持多种策略：
    1. random - 简单随机选择
    2. weighted - 加权随机选择（默认）
    3. lowest_cost - 最低成本优先
    4. performance - 最高性能优先
    
    附加功能：
    - 健康检查
    - 延迟分析（基于日志）
    - 可选的缓存感知路由
    """
    
    def __init__(self):
        # 内存中的健康状态缓存
        self._health_status: Dict[int, ChannelHealthStatus] = {}
        # 性能指标缓存
        self._performance_metrics: Dict[Tuple[int, str], ChannelPerformanceMetrics] = {}
        # 缓存路由信息
        self._cache_routing: Dict[Tuple[int, str], CacheRoutingInfo] = {}
        # 渠道连续失败次数
        self._consecutive_failures: Dict[int, int] = defaultdict(int)
        
        # 配置参数
        self.health_check_timeout = 10
        self.metrics_window_minutes = 30
        self.cache_routing_ttl_minutes = 5
        self.max_consecutive_failures = 3
        self.latency_weight_factor = 0.3
        
        # 默认策略
        self.default_strategy = LoadBalanceStrategy.WEIGHTED_RANDOM
        
        # 缓存追踪开关（默认开启）
        self.enable_cache_tracking = True
        
    def set_cache_tracking(self, enabled: bool) -> None:
        """设置缓存追踪开关.
        
        Args:
            enabled: 是否启用缓存追踪
        """
        self.enable_cache_tracking = enabled
        logger.info(f"Cache tracking {'enabled' if enabled else 'disabled'}")
    
    def set_default_strategy(self, strategy: LoadBalanceStrategy) -> None:
        """设置默认负载均衡策略.
        
        Args:
            strategy: 策略类型
        """
        self.default_strategy = strategy
        logger.info(f"Default load balance strategy set to: {strategy.value}")
    
    async def check_channel_health(
        self,
        channel: Channel,
        db: AsyncSession,
    ) -> ChannelHealthStatus:
        """检查单个渠道的健康状态."""
        start_time = time.time()
        config = channel.config
        
        try:
            if channel.type == "openai":
                is_healthy = await self._check_openai_health(channel, config)
            elif channel.type == "azure":
                is_healthy = await self._check_azure_health(channel, config)
            elif channel.type == "anthropic":
                is_healthy = await self._check_anthropic_health(channel, config)
            elif channel.type == "gemini":
                is_healthy = await self._check_gemini_health(channel, config)
            else:
                is_healthy = True
                
            check_latency_ms = int((time.time() - start_time) * 1000)
            
            if is_healthy:
                self._consecutive_failures[channel.id] = 0
                status = ChannelHealthStatus(
                    channel_id=channel.id,
                    is_healthy=True,
                    last_check_time=datetime.utcnow(),
                    consecutive_failures=0,
                    check_latency_ms=check_latency_ms,
                    message="Healthy",
                )
            else:
                self._consecutive_failures[channel.id] += 1
                status = ChannelHealthStatus(
                    channel_id=channel.id,
                    is_healthy=False,
                    last_check_time=datetime.utcnow(),
                    consecutive_failures=self._consecutive_failures[channel.id],
                    check_latency_ms=check_latency_ms,
                    message="Health check failed",
                )
                
        except Exception as e:
            self._consecutive_failures[channel.id] += 1
            status = ChannelHealthStatus(
                channel_id=channel.id,
                is_healthy=False,
                last_check_time=datetime.utcnow(),
                consecutive_failures=self._consecutive_failures[channel.id],
                check_latency_ms=int((time.time() - start_time) * 1000),
                message=str(e),
            )
        
        self._health_status[channel.id] = status
        return status
    
    async def _check_openai_health(self, channel: Channel, config: dict) -> bool:
        """检查OpenAI渠道健康状态."""
        api_base = config.get("api_base", "https://api.openai.com")
        api_key = config.get("api_key")
        
        if not api_key:
            return False
            
        async with httpx.AsyncClient(timeout=self.health_check_timeout) as client:
            try:
                response = await client.get(
                    f"{api_base}/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                return response.status_code == 200
            except Exception:
                return False
    
    async def _check_azure_health(self, channel: Channel, config: dict) -> bool:
        """检查Azure渠道健康状态."""
        api_base = config.get("api_base")
        api_key = config.get("api_key")
        api_version = config.get("api_version", "2024-02-01")
        
        if not api_base or not api_key:
            return False
            
        async with httpx.AsyncClient(timeout=self.health_check_timeout) as client:
            try:
                response = await client.get(
                    f"{api_base}/openai/models?api-version={api_version}",
                    headers={"api-key": api_key},
                )
                return response.status_code == 200
            except Exception:
                return False
    
    async def _check_anthropic_health(self, channel: Channel, config: dict) -> bool:
        """检查Anthropic渠道健康状态."""
        api_base = config.get("api_base", "https://api.anthropic.com")
        api_key = config.get("api_key")
        
        if not api_key:
            return False
            
        async with httpx.AsyncClient(timeout=self.health_check_timeout) as client:
            try:
                response = await client.post(
                    f"{api_base}/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "claude-3-haiku-20240307",
                        "max_tokens": 1,
                        "messages": [{"role": "user", "content": "hi"}],
                    },
                )
                return response.status_code in [200, 400, 429]
            except Exception:
                return False
    
    async def _check_gemini_health(self, channel: Channel, config: dict) -> bool:
        """检查Gemini渠道健康状态."""
        api_key = config.get("api_key")
        api_base = config.get("api_base", "https://generativelanguage.googleapis.com")
        api_version = config.get("api_version", "v1beta")
        
        if not api_key:
            return False
            
        async with httpx.AsyncClient(timeout=self.health_check_timeout) as client:
            try:
                response = await client.get(
                    f"{api_base}/{api_version}/models?key={api_key}",
                )
                return response.status_code == 200
            except Exception:
                return False
    
    async def analyze_channel_performance(
        self,
        channel_id: int,
        model: str,
        db: AsyncSession,
        window_minutes: Optional[int] = None,
    ) -> ChannelPerformanceMetrics:
        """分析渠道性能指标（基于日志）."""
        if window_minutes is None:
            window_minutes = self.metrics_window_minutes
            
        since = datetime.utcnow() - timedelta(minutes=window_minutes)
        
        result = await db.execute(
            select(RequestLog).where(
                and_(
                    RequestLog.channel_id == channel_id,
                    RequestLog.model == model,
                    RequestLog.created_at >= since,
                )
            )
        )
        
        logs = result.scalars().all()
        
        if not logs:
            return ChannelPerformanceMetrics(
                channel_id=channel_id,
                model=model,
                avg_latency_ms=0.0,
                p50_latency_ms=0.0,
                p95_latency_ms=0.0,
                p99_latency_ms=0.0,
                success_rate=1.0,
                total_requests=0,
            )
        
        success_logs = [log for log in logs if log.status == "success"]
        error_logs = [log for log in logs if log.status == "error"]
        
        total_requests = len(logs)
        error_count = len(error_logs)
        success_rate = len(success_logs) / total_requests if total_requests > 0 else 1.0
        
        latencies = [log.latency_ms for log in success_logs if log.latency_ms is not None]
        
        if latencies:
            latencies_sorted = sorted(latencies)
            avg_latency = statistics.mean(latencies)
            p50 = latencies_sorted[len(latencies_sorted) // 2]
            p95_idx = int(len(latencies_sorted) * 0.95)
            p99_idx = int(len(latencies_sorted) * 0.99)
            p95 = latencies_sorted[min(p95_idx, len(latencies_sorted) - 1)]
            p99 = latencies_sorted[min(p99_idx, len(latencies_sorted) - 1)]
        else:
            avg_latency = p50 = p95 = p99 = 0.0
        
        cached_requests = sum(1 for lat in latencies if lat < 50)
        cache_hit_rate = cached_requests / len(latencies) if latencies else 0.0
        
        metrics = ChannelPerformanceMetrics(
            channel_id=channel_id,
            model=model,
            avg_latency_ms=avg_latency,
            p50_latency_ms=p50,
            p95_latency_ms=p95,
            p99_latency_ms=p99,
            success_rate=success_rate,
            total_requests=total_requests,
            error_count=error_count,
            cached_requests=cached_requests,
            cache_hit_rate=cache_hit_rate,
        )
        
        self._performance_metrics[(channel_id, model)] = metrics
        return metrics
    
    async def get_channel_performance(
        self,
        channel_id: int,
        model: str,
        db: AsyncSession,
        use_cache: bool = True,
    ) -> ChannelPerformanceMetrics:
        """获取渠道性能指标（带缓存）."""
        cache_key = (channel_id, model)
        
        if use_cache and cache_key in self._performance_metrics:
            cached = self._performance_metrics[cache_key]
            if datetime.utcnow() - cached.calculated_at < timedelta(minutes=5):
                return cached
        
        return await self.analyze_channel_performance(channel_id, model, db)
    
    def get_channel_cost_info(
        self,
        channel: Channel,
        model: str,
    ) -> ChannelCostInfo:
        """获取渠道成本信息.
        
        从渠道配置中读取成本配置，如果没有则使用默认值。
        """
        config = channel.config
        
        # 尝试从配置的模型特定成本获取
        model_costs = config.get("model_costs", {})
        if model in model_costs:
            cost_config = model_costs[model]
            return ChannelCostInfo(
                channel_id=channel.id,
                model=model,
                input_cost_per_1k=cost_config.get("input", 0.01),
                output_cost_per_1k=cost_config.get("output", 0.03),
            )
        
        # 使用渠道默认成本配置
        default_costs = config.get("default_costs", {})
        if default_costs:
            return ChannelCostInfo(
                channel_id=channel.id,
                model=model,
                input_cost_per_1k=default_costs.get("input", 0.01),
                output_cost_per_1k=default_costs.get("output", 0.03),
            )
        
        # 根据渠道类型使用默认成本
        default_pricing = {
            "openai": {"input": 0.01, "output": 0.03},
            "azure": {"input": 0.01, "output": 0.03},
            "anthropic": {"input": 0.008, "output": 0.024},
            "gemini": {"input": 0.0005, "output": 0.0015},
        }
        
        pricing = default_pricing.get(channel.type, {"input": 0.01, "output": 0.03})
        
        return ChannelCostInfo(
            channel_id=channel.id,
            model=model,
            input_cost_per_1k=pricing["input"],
            output_cost_per_1k=pricing["output"],
        )
    
    def update_cache_routing(
        self,
        user_id: int,
        model: str,
        channel_id: int,
        has_cache_enabled: bool = True,
    ) -> None:
        """更新缓存路由信息."""
        if not self.enable_cache_tracking:
            return
            
        key = (user_id, model)
        now = datetime.utcnow()
        
        if key in self._cache_routing:
            existing = self._cache_routing[key]
            if existing.channel_id == channel_id:
                existing.consecutive_hits += 1
                existing.last_used_at = now
            else:
                self._cache_routing[key] = CacheRoutingInfo(
                    channel_id=channel_id,
                    model=model,
                    has_cache_enabled=has_cache_enabled,
                    last_used_at=now,
                    consecutive_hits=1,
                )
        else:
            self._cache_routing[key] = CacheRoutingInfo(
                channel_id=channel_id,
                model=model,
                has_cache_enabled=has_cache_enabled,
                last_used_at=now,
                consecutive_hits=1,
            )
    
    def get_cache_routing_preference(
        self,
        user_id: int,
        model: str,
    ) -> Optional[CacheRoutingInfo]:
        """获取缓存路由偏好."""
        if not self.enable_cache_tracking:
            return None
            
        key = (user_id, model)
        
        if key not in self._cache_routing:
            return None
            
        info = self._cache_routing[key]
        
        if datetime.utcnow() - info.last_used_at > timedelta(minutes=self.cache_routing_ttl_minutes):
            del self._cache_routing[key]
            return None
            
        return info
    
    def is_channel_healthy(self, channel_id: int) -> bool:
        """快速检查渠道是否健康."""
        if self._consecutive_failures.get(channel_id, 0) >= self.max_consecutive_failures:
            return False
            
        if channel_id in self._health_status:
            status = self._health_status[channel_id]
            if datetime.utcnow() - status.last_check_time < timedelta(minutes=5):
                return status.is_healthy
                
        return True
    
    def _filter_healthy_channels(
        self,
        channels: List[Tuple[Channel, ModelMapping]],
    ) -> List[Tuple[Channel, ModelMapping]]:
        """过滤出健康的渠道."""
        healthy = [(ch, m) for ch, m in channels if self.is_channel_healthy(ch.id)]
        return healthy if healthy else channels
    
    async def _strategy_random(
        self,
        channels: List[Tuple[Channel, ModelMapping]],
        model: str,
        db: AsyncSession,
    ) -> Optional[Tuple[Channel, ModelMapping]]:
        """策略1: 简单随机选择.
        
        完全随机，不考虑权重、性能或成本。
        """
        if not channels:
            return None
        
        # 过滤健康渠道
        healthy_channels = self._filter_healthy_channels(channels)
        
        # 完全随机选择
        selected = random.choice(healthy_channels)
        logger.info(f"Random strategy: selected channel {selected[0].id} for model {model}")
        return selected
    
    async def _strategy_weighted_random(
        self,
        channels: List[Tuple[Channel, ModelMapping]],
        model: str,
        db: AsyncSession,
    ) -> Optional[Tuple[Channel, ModelMapping]]:
        """策略2: 加权随机选择（原始策略）.
        
        基于配置的权重进行加权随机选择。
        """
        if not channels:
            return None
        
        # 过滤健康渠道
        healthy_channels = self._filter_healthy_channels(channels)
        
        # 按权重加权随机选择
        total_weight = sum(ch.weight for ch, _ in healthy_channels)
        r = random.uniform(0, total_weight)
        
        cumulative = 0
        for channel, mapping in healthy_channels:
            cumulative += channel.weight
            if r <= cumulative:
                logger.info(
                    f"Weighted random strategy: selected channel {channel.id} "
                    f"for model {model} (weight={channel.weight})"
                )
                return channel, mapping
        
        return healthy_channels[0]
    
    async def _strategy_lowest_cost(
        self,
        channels: List[Tuple[Channel, ModelMapping]],
        model: str,
        db: AsyncSession,
    ) -> Optional[Tuple[Channel, ModelMapping]]:
        """策略3: 最低成本优先.
        
        选择成本最低的渠道，如果有多个相同成本的渠道则随机选择。
        考虑成功率作为惩罚因子。
        """
        if not channels:
            return None
        
        # 过滤健康渠道
        healthy_channels = self._filter_healthy_channels(channels)
        
        # 计算每个渠道的成本得分
        channel_costs = []
        for channel, mapping in healthy_channels:
            cost_info = self.get_channel_cost_info(channel, model)
            
            # 获取性能指标（成功率）
            metrics = await self.get_channel_performance(channel.id, model, db)
            success_rate = metrics.success_rate if metrics.total_requests > 0 else 1.0
            
            # 成本得分 = 平均成本 / 成功率（成功率越低，成本惩罚越高）
            cost_score = cost_info.average_cost_per_request / max(success_rate, 0.1)
            
            channel_costs.append((channel, mapping, cost_score, cost_info))
        
        if not channel_costs:
            return None
        
        # 按成本排序，选择最低成本的
        channel_costs.sort(key=lambda x: x[2])
        
        # 如果有多个相同最低成本的渠道，在前3个中随机选择（增加一些随机性避免总是选同一个）
        lowest_cost = channel_costs[0][2]
        candidates = [(ch, m) for ch, m, cost, _ in channel_costs if abs(cost - lowest_cost) < 0.001]
        
        if len(candidates) > 3:
            candidates = candidates[:3]
        
        selected = random.choice(candidates)
        selected_cost = next(c for ch, m, c, _ in channel_costs if ch.id == selected[0].id)
        
        logger.info(
            f"Lowest cost strategy: selected channel {selected[0].id} for model {model} "
            f"(cost_score={selected_cost:.6f})"
        )
        return selected
    
    async def _strategy_best_performance(
        self,
        channels: List[Tuple[Channel, ModelMapping]],
        model: str,
        db: AsyncSession,
    ) -> Optional[Tuple[Channel, ModelMapping]]:
        """策略4: 最高性能优先.
        
        基于P95延迟和成功率综合评分，选择性能最好的渠道。
        """
        if not channels:
            return None
        
        # 过滤健康渠道
        healthy_channels = self._filter_healthy_channels(channels)
        
        # 计算每个渠道的性能得分
        channel_scores = []
        for channel, mapping in healthy_channels:
            metrics = await self.get_channel_performance(channel.id, model, db)
            
            if metrics.total_requests > 0:
                # P95延迟得分（越低越好，归一化到0-1）
                # 假设优秀延迟为500ms，较差为10000ms
                latency_score = max(0, 1 - (metrics.p95_latency_ms / 10000))
                
                # 成功率权重更高
                success_weight = 0.7
                latency_weight = 0.3
                
                # 综合得分
                performance_score = (
                    success_weight * metrics.success_rate +
                    latency_weight * latency_score
                )
            else:
                # 没有历史数据，使用默认得分
                performance_score = 0.5
            
            channel_scores.append((channel, mapping, performance_score, metrics))
        
        if not channel_scores:
            return None
        
        # 按性能得分排序（降序）
        channel_scores.sort(key=lambda x: x[2], reverse=True)
        
        # 在前3个高性能渠道中随机选择（避免总是选同一个）
        candidates = channel_scores[:min(3, len(channel_scores))]
        selected = random.choice(candidates)
        
        logger.info(
            f"Best performance strategy: selected channel {selected[0].id} for model {model} "
            f"(score={selected[2]:.3f}, p95={selected[3].p95_latency_ms}ms, "
            f"success={selected[3].success_rate:.2%})"
        )
        return selected[0], selected[1]
    
    async def select_optimal_channel(
        self,
        model: str,
        user_id: int,
        db: AsyncSession,
        strategy: Optional[LoadBalanceStrategy] = None,
        prefer_cache: Optional[bool] = None,
    ) -> Optional[Tuple[Channel, ModelMapping]]:
        """选择最优渠道（支持多种策略）.
        
        Args:
            model: 模型ID
            user_id: 用户ID
            db: 数据库会话
            strategy: 负载均衡策略，None则使用默认策略
            prefer_cache: 是否优先使用缓存路由，None则使用全局配置
            
        Returns:
            选中的渠道和映射
        """
        # 使用默认策略
        if strategy is None:
            strategy = self.default_strategy
        
        # 使用全局缓存配置
        if prefer_cache is None:
            prefer_cache = self.enable_cache_tracking
        
        # 查找支持该模型的所有活跃渠道
        result = await db.execute(
            select(Channel, ModelMapping)
            .join(ModelMapping, Channel.id == ModelMapping.channel_id)
            .where(
                and_(
                    Channel.status == "active",
                    ModelMapping.model_id == model,
                )
            )
        )
        
        channels = [(row.Channel, row.ModelMapping) for row in result.all()]
        
        if not channels:
            logger.warning(f"No channels found for model {model}")
            return None
        
        # 检查缓存路由偏好（仅在启用缓存追踪时）
        if prefer_cache and self.enable_cache_tracking:
            cache_info = self.get_cache_routing_preference(user_id, model)
            if cache_info and cache_info.has_cache_enabled:
                for channel, mapping in channels:
                    if channel.id == cache_info.channel_id:
                        if self.is_channel_healthy(channel.id):
                            logger.info(
                                f"Cache routing: selecting channel {channel.id} "
                                f"for user {user_id}, model {model} "
                                f"(consecutive hits: {cache_info.consecutive_hits})"
                            )
                            return channel, mapping
                        break
        
        # 根据策略选择渠道
        if strategy == LoadBalanceStrategy.RANDOM:
            return await self._strategy_random(channels, model, db)
        elif strategy == LoadBalanceStrategy.WEIGHTED_RANDOM:
            return await self._strategy_weighted_random(channels, model, db)
        elif strategy == LoadBalanceStrategy.LOWEST_COST:
            return await self._strategy_lowest_cost(channels, model, db)
        elif strategy == LoadBalanceStrategy.BEST_PERFORMANCE:
            return await self._strategy_best_performance(channels, model, db)
        else:
            # 默认使用加权随机
            return await self._strategy_weighted_random(channels, model, db)
    
    async def check_all_channels_health(self, db: AsyncSession) -> Dict[int, ChannelHealthStatus]:
        """检查所有渠道的健康状态."""
        result = await db.execute(select(Channel).where(Channel.status == "active"))
        channels = result.scalars().all()
        
        tasks = [self.check_channel_health(channel, db) for channel in channels]
        statuses = await asyncio.gather(*tasks, return_exceptions=True)
        
        results = {}
        for channel, status in zip(channels, statuses):
            if isinstance(status, Exception):
                logger.error(f"Health check failed for channel {channel.id}: {status}")
                status = ChannelHealthStatus(
                    channel_id=channel.id,
                    is_healthy=False,
                    last_check_time=datetime.utcnow(),
                    consecutive_failures=self._consecutive_failures.get(channel.id, 0) + 1,
                    message=str(status),
                )
                self._consecutive_failures[channel.id] = status.consecutive_failures
                self._health_status[channel.id] = status
            results[channel.id] = status
        
        return results
    
    def record_request_result(
        self,
        channel_id: int,
        model: str,
        user_id: int,
        success: bool,
        latency_ms: int,
        has_cache: bool = False,
    ) -> None:
        """记录请求结果."""
        if success:
            if channel_id in self._consecutive_failures:
                del self._consecutive_failures[channel_id]
            
            # 仅在启用缓存追踪时更新
            if self.enable_cache_tracking and (has_cache or latency_ms < 50):
                self.update_cache_routing(user_id, model, channel_id, has_cache_enabled=True)
        else:
            self._consecutive_failures[channel_id] += 1
            if self.enable_cache_tracking:
                key = (user_id, model)
                if key in self._cache_routing:
                    cache_info = self._cache_routing[key]
                    if cache_info.channel_id == channel_id:
                        del self._cache_routing[key]


# 全局负载均衡服务实例
load_balancer = LoadBalancerService()
