"""
用量统计接口
提供用量查询和统计功能
"""

from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db
from app.db.models.request_log import RequestLog
from app.db.models.usage_stats import UsageStats
from app.db.models.user import User as UserModel
from app.schemas import PaginatedResponse, ResponseModel

router = APIRouter()


class UsageSummaryItem(BaseModel):
    """用量汇总项."""
    
    model: str = Field(..., description="模型名称")
    requests: int = Field(..., description="请求次数")
    tokens_input: int = Field(..., description="输入token数")
    tokens_output: int = Field(..., description="输出token数")
    cost: float = Field(..., description="费用")


class DailyUsageItem(BaseModel):
    """每日用量项."""
    
    date: str = Field(..., description="日期")
    requests: int = Field(..., description="请求次数")
    tokens: int = Field(..., description="总token数")
    cost: float = Field(..., description="费用")


class UsageSummaryResponse(BaseModel):
    """用量汇总响应."""
    
    period: dict = Field(..., description="统计周期")
    total_requests: int = Field(..., description="总请求数")
    total_tokens: int = Field(..., description="总token数")
    total_cost: float = Field(..., description="总费用")
    by_model: list = Field(default=[], description="按模型统计")
    by_day: list = Field(default=[], description="按天统计")


class RequestLogItem(BaseModel):
    """请求日志项."""
    
    id: int = Field(..., description="日志ID")
    model: str = Field(..., description="模型")
    status: str = Field(..., description="状态")
    tokens_input: int = Field(..., description="输入token数")
    tokens_output: int = Field(..., description="输出token数")
    cost: float = Field(..., description="费用")
    latency_ms: int = Field(..., description="延迟（毫秒）")
    created_at: datetime = Field(..., description="请求时间")
    error_message: Optional[str] = Field(None, description="错误信息")


@router.get("/summary", response_model=ResponseModel[UsageSummaryResponse])
async def get_usage_summary(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """获取用量汇总.
    
    Args:
        start_date: 开始日期（默认30天前）
        end_date: 结束日期（默认今天）
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        用量汇总数据
    """
    # 设置默认日期范围
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    # 查询总用量
    result = await db.execute(
        select(
            func.count().label("requests"),
            func.coalesce(func.sum(RequestLog.tokens_input), 0).label("tokens_input"),
            func.coalesce(func.sum(RequestLog.tokens_output), 0).label("tokens_output"),
            func.coalesce(func.sum(RequestLog.cost), 0).label("cost"),
        )
        .where(
            RequestLog.user_id == current_user.id,
            RequestLog.created_at >= datetime.combine(start_date, datetime.min.time()),
            RequestLog.created_at <= datetime.combine(end_date, datetime.max.time()),
        )
    )
    row = result.one()
    
    # 按模型统计
    model_result = await db.execute(
        select(
            RequestLog.model,
            func.count().label("requests"),
            func.coalesce(func.sum(RequestLog.tokens_input), 0).label("tokens_input"),
            func.coalesce(func.sum(RequestLog.tokens_output), 0).label("tokens_output"),
            func.coalesce(func.sum(RequestLog.cost), 0).label("cost"),
        )
        .where(
            RequestLog.user_id == current_user.id,
            RequestLog.created_at >= datetime.combine(start_date, datetime.min.time()),
            RequestLog.created_at <= datetime.combine(end_date, datetime.max.time()),
        )
        .group_by(RequestLog.model)
    )
    
    by_model = [
        UsageSummaryItem(
            model=m.model,
            requests=m.requests,
            tokens_input=m.tokens_input,
            tokens_output=m.tokens_output,
            cost=float(m.cost),
        )
        for m in model_result.all()
    ]
    
    # 按天统计
    daily_result = await db.execute(
        select(
            func.date(RequestLog.created_at).label("date"),
            func.count().label("requests"),
            func.coalesce(func.sum(RequestLog.tokens_input + RequestLog.tokens_output), 0).label("tokens"),
            func.coalesce(func.sum(RequestLog.cost), 0).label("cost"),
        )
        .where(
            RequestLog.user_id == current_user.id,
            RequestLog.created_at >= datetime.combine(start_date, datetime.min.time()),
            RequestLog.created_at <= datetime.combine(end_date, datetime.max.time()),
        )
        .group_by(func.date(RequestLog.created_at))
        .order_by(func.date(RequestLog.created_at))
    )
    
    by_day = [
        DailyUsageItem(
            date=str(d.date),
            requests=d.requests,
            tokens=d.tokens,
            cost=float(d.cost),
        )
        for d in daily_result.all()
    ]
    
    return ResponseModel(
        code=200,
        message="success",
        data=UsageSummaryResponse(
            period={"start": str(start_date), "end": str(end_date)},
            total_requests=row.requests or 0,
            total_tokens=(row.tokens_input or 0) + (row.tokens_output or 0),
            total_cost=float(row.cost or 0),
            by_model=by_model,
            by_day=by_day,
        ),
    )


@router.get("/logs", response_model=ResponseModel[PaginatedResponse[RequestLogItem]])
async def get_request_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    model: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """获取请求日志列表.
    
    Args:
        page: 页码
        page_size: 每页数量
        model: 模型筛选
        status: 状态筛选
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        请求日志列表（分页）
    """
    query = select(RequestLog).where(RequestLog.user_id == current_user.id)
    
    if model:
        query = query.where(RequestLog.model == model)
    if status:
        query = query.where(RequestLog.status == status)
    
    # 总数
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar()
    
    # 分页
    query = query.order_by(RequestLog.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    items = [
        RequestLogItem(
            id=log.id,
            model=log.model,
            status=log.status,
            tokens_input=log.tokens_input or 0,
            tokens_output=log.tokens_output or 0,
            cost=float(log.cost or 0),
            latency_ms=log.latency_ms or 0,
            created_at=log.created_at,
            error_message=log.error_message,
        )
        for log in logs
    ]
    
    total_pages = (total + page_size - 1) // page_size
    
    return ResponseModel(
        code=200,
        message="success",
        data=PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ),
    )
