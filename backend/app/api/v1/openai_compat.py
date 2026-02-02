"""
OpenAI 兼容接口
提供与OpenAI API完全兼容的接口
"""

import json
import time
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional

import httpx
from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_api_key, get_db
from app.core.config import settings
from app.core.exceptions import NotFoundError, RateLimitError, UpstreamError, ValidationError
from app.core.logging import logger
from app.db.models.api_key import APIKey
from app.db.models.channel import Channel
from app.db.models.model_def import ModelDef
from app.db.models.model_mapping import ModelMapping
from app.db.models.request_log import RequestLog

router = APIRouter()


# ===== 请求/响应模型 =====

class ChatMessage(BaseModel):
    """聊天消息."""
    
    role: str = Field(..., description="角色 (system/user/assistant)")
    content: str = Field(..., description="内容")


class ChatCompletionRequest(BaseModel):
    """聊天完成请求."""
    
    model: str = Field(..., description="模型ID")
    messages: list[ChatMessage] = Field(..., description="消息列表")
    temperature: Optional[float] = Field(default=0.7, ge=0, le=2)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    stream: bool = Field(default=False, description="是否流式响应")
    top_p: Optional[float] = Field(default=1.0, ge=0, le=1)
    frequency_penalty: Optional[float] = Field(default=0, ge=-2, le=2)
    presence_penalty: Optional[float] = Field(default=0, ge=-2, le=2)


class ChatCompletionChoice(BaseModel):
    """聊天完成选项."""
    
    index: int = Field(default=0)
    message: ChatMessage
    finish_reason: Optional[str] = Field(default=None)


class ChatCompletionChunkChoice(BaseModel):
    """流式响应选项."""
    
    index: int = Field(default=0)
    delta: dict = Field(default_factory=dict)
    finish_reason: Optional[str] = Field(default=None)


class Usage(BaseModel):
    """用量信息."""
    
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    """聊天完成响应."""
    
    id: str
    object: str = Field(default="chat.completion")
    created: int
    model: str
    choices: list[ChatCompletionChoice]
    usage: Usage


class ChatCompletionChunk(BaseModel):
    """流式响应块."""
    
    id: str
    object: str = Field(default="chat.completion.chunk")
    created: int
    model: str
    choices: list[ChatCompletionChunkChoice]


class ModelInfo(BaseModel):
    """模型信息."""
    
    id: str
    object: str = Field(default="model")
    created: int = Field(default=0)
    owned_by: str = Field(default="openai")


class ModelsResponse(BaseModel):
    """模型列表响应."""
    
    object: str = Field(default="list")
    data: list[ModelInfo]


# ===== 辅助函数 =====

def count_tokens(text: str) -> int:
    """估算token数（简化版）.
    
    实际应用中应使用tiktoken等库
    
    Args:
        text: 文本
        
    Returns:
        估算的token数
    """
    # 简单估算：英文约4字符/token，中文约2字符/token
    # 这里使用保守估计
    return len(text) // 3 + 1


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """计算费用.
    
    Args:
        model: 模型名称
        input_tokens: 输入token数
        output_tokens: 输出token数
        
    Returns:
        费用（美元）
    """
    # 默认价格（每1K tokens）
    pricing = {
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "gpt-3.5-turbo-16k": {"input": 0.001, "output": 0.002},
    }
    
    # 获取模型价格
    model_pricing = pricing.get(model, pricing.get("gpt-3.5-turbo"))
    
    input_cost = (input_tokens / 1000) * model_pricing["input"]
    output_cost = (output_tokens / 1000) * model_pricing["output"]
    
    return round(input_cost + output_cost, 6)


async def select_channel_for_model(
    model: str,
    db: AsyncSession,
) -> Optional[Channel]:
    """为指定模型选择合适的渠道.
    
    简单的负载均衡策略：按权重随机选择
    
    Args:
        model: 模型ID
        db: 数据库会话
        
    Returns:
        选中的渠道
    """
    # 查找支持该模型的渠道
    result = await db.execute(
        select(Channel, ModelMapping)
        .join(ModelMapping, Channel.id == ModelMapping.channel_id)
        .where(
            Channel.status == "active",
            ModelMapping.model_id == model,
        )
    )
    
    channels = []
    for row in result.all():
        channel = row.Channel
        mapping = row.ModelMapping
        channels.append((channel, mapping))
    
    if not channels:
        return None, None
    
    # 简单策略：选择权重最高的
    # 实际应用中可以更复杂（健康检查、延迟测试等）
    import random
    
    # 按权重加权随机选择
    total_weight = sum(ch.weight for ch, _ in channels)
    r = random.uniform(0, total_weight)
    
    cumulative = 0
    for channel, mapping in channels:
        cumulative += channel.weight
        if r <= cumulative:
            return channel, mapping
    
    return channels[0]


async def log_request(
    db: AsyncSession,
    api_key_id: int,
    user_id: int,
    channel_id: int,
    model: str,
    status: str,
    tokens_input: int,
    tokens_output: int,
    cost: float,
    latency_ms: int,
    error_message: Optional[str] = None,
):
    """记录请求日志.
    
    Args:
        db: 数据库会话
        api_key_id: API Key ID
        user_id: 用户ID
        channel_id: 渠道ID
        model: 模型
        status: 状态
        tokens_input: 输入token数
        tokens_output: 输出token数
        cost: 费用
        latency_ms: 延迟毫秒
        error_message: 错误信息
    """
    log = RequestLog(
        api_key_id=api_key_id,
        user_id=user_id,
        channel_id=channel_id,
        model=model,
        status=status,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        cost=cost,
        latency_ms=latency_ms,
        error_message=error_message,
    )
    db.add(log)
    await db.commit()


# ===== API 端点 =====

@router.get("/models", response_model=ModelsResponse)
async def list_models(
    api_key: APIKey = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db),
):
    """获取可用模型列表.
    
    返回OpenAI兼容格式的模型列表
    
    Args:
        api_key: API Key
        db: 数据库会话
        
    Returns:
        模型列表
    """
    # 获取API Key允许的模型
    if api_key.allowed_models:
        model_ids = api_key.allowed_models
    else:
        # 获取所有活跃模型
        result = await db.execute(
            select(ModelDef).where(ModelDef.status == "active")
        )
        models = result.scalars().all()
        model_ids = [m.id for m in models]
    
    # 构建响应
    model_infos = [
        ModelInfo(
            id=model_id,
            created=int(datetime.now(timezone.utc).timestamp()),
            owned_by="openai",
        )
        for model_id in model_ids
    ]
    
    return ModelsResponse(data=model_infos)


@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    api_key: APIKey = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db),
):
    """聊天完成接口.
    
    OpenAI兼容的聊天完成接口，支持流式和非流式响应
    
    Args:
        request: 请求体
        api_key: API Key
        db: 数据库会话
        
    Returns:
        聊天完成响应（流式或非流式）
    """
    start_time = time.time()
    
    # 检查API Key是否允许使用该模型
    if api_key.allowed_models and request.model not in api_key.allowed_models:
        raise ValidationError(f"API Key无权访问模型: {request.model}")
    
    # 选择渠道
    channel, mapping = await select_channel_for_model(request.model, db)
    
    if not channel:
        raise NotFoundError(f"找不到支持模型 {request.model} 的渠道")
    
    # 计算输入token数
    input_text = "\n".join([m.content for m in request.messages])
    input_tokens = count_tokens(input_text)
    
    # 准备上游请求
    upstream_model = mapping.mapped_model if mapping else request.model
    
    if request.stream:
        # 流式响应
        return StreamingResponse(
            stream_chat_completion(
                request=request,
                api_key=api_key,
                channel=channel,
                upstream_model=upstream_model,
                input_tokens=input_tokens,
                start_time=start_time,
                db=db,
            ),
            media_type="text/event-stream",
        )
    else:
        # 非流式响应
        return await non_stream_chat_completion(
            request=request,
            api_key=api_key,
            channel=channel,
            upstream_model=upstream_model,
            input_tokens=input_tokens,
            start_time=start_time,
            db=db,
        )


async def non_stream_chat_completion(
    request: ChatCompletionRequest,
    api_key: APIKey,
    channel: Channel,
    upstream_model: str,
    input_tokens: int,
    start_time: float,
    db: AsyncSession,
) -> ChatCompletionResponse:
    """非流式聊天完成.
    
    Args:
        request: 请求
        api_key: API Key
        channel: 渠道
        upstream_model: 上游模型名称
        input_tokens: 输入token数
        start_time: 开始时间
        db: 数据库会话
        
    Returns:
        聊天完成响应
    """
    config = channel.config
    latency_ms = 0
    
    try:
        # 构建上游请求
        upstream_request = {
            "model": upstream_model,
            "messages": [m.model_dump() for m in request.messages],
            "temperature": request.temperature,
            "top_p": request.top_p,
            "frequency_penalty": request.frequency_penalty,
            "presence_penalty": request.presence_penalty,
            "stream": False,
        }
        
        if request.max_tokens:
            upstream_request["max_tokens"] = request.max_tokens
        
        # 发送请求到上游
        async with httpx.AsyncClient(timeout=settings.UPSTREAM_TIMEOUT) as client:
            if channel.type == "openai":
                api_base = config.get("api_base", "https://api.openai.com")
                headers = {
                    "Authorization": f"Bearer {config['api_key']}",
                    "Content-Type": "application/json",
                }
                
                response = await client.post(
                    f"{api_base}/v1/chat/completions",
                    headers=headers,
                    json=upstream_request,
                )
                response.raise_for_status()
                upstream_data = response.json()
                
            elif channel.type == "azure":
                api_base = config["api_base"]
                api_version = config.get("api_version", "2024-02-01")
                
                response = await client.post(
                    f"{api_base}/openai/deployments/{upstream_model}/chat/completions?api-version={api_version}",
                    headers={
                        "api-key": config["api_key"],
                        "Content-Type": "application/json",
                    },
                    json=upstream_request,
                )
                response.raise_for_status()
                upstream_data = response.json()
            
            else:
                # 其他供应商简化处理
                raise UpstreamError(f"暂不支持渠道类型: {channel.type}")
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        # 提取响应信息
        content = upstream_data["choices"][0]["message"]["content"]
        finish_reason = upstream_data["choices"][0].get("finish_reason")
        
        # 获取或计算token数
        if "usage" in upstream_data:
            output_tokens = upstream_data["usage"].get("completion_tokens", 0)
            total_tokens = upstream_data["usage"].get("total_tokens", input_tokens + output_tokens)
        else:
            output_tokens = count_tokens(content)
            total_tokens = input_tokens + output_tokens
        
        # 计算费用
        cost = calculate_cost(request.model, input_tokens, output_tokens)
        
        # 记录日志
        await log_request(
            db=db,
            api_key_id=api_key.id,
            user_id=api_key.user_id,
            channel_id=channel.id,
            model=request.model,
            status="success",
            tokens_input=input_tokens,
            tokens_output=output_tokens,
            cost=cost,
            latency_ms=latency_ms,
        )
        
        # 更新API Key使用量
        api_key.budget_used = float(api_key.budget_used) + cost
        await db.commit()
        
        # 构建响应
        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:10]}",
            created=int(datetime.now(timezone.utc).timestamp()),
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content=content),
                    finish_reason=finish_reason,
                )
            ],
            usage=Usage(
                prompt_tokens=input_tokens,
                completion_tokens=output_tokens,
                total_tokens=total_tokens,
            ),
        )
    
    except httpx.HTTPStatusError as e:
        latency_ms = int((time.time() - start_time) * 1000)
        
        error_msg = f"上游服务错误: {e.response.status_code}"
        try:
            error_data = e.response.json()
            if "error" in error_data:
                error_msg = error_data["error"].get("message", error_msg)
        except:
            pass
        
        # 记录错误日志
        await log_request(
            db=db,
            api_key_id=api_key.id,
            user_id=api_key.user_id,
            channel_id=channel.id,
            model=request.model,
            status="error",
            tokens_input=input_tokens,
            tokens_output=0,
            cost=0,
            latency_ms=latency_ms,
            error_message=error_msg,
        )
        
        raise UpstreamError(error_msg)
    
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        
        # 记录错误日志
        await log_request(
            db=db,
            api_key_id=api_key.id,
            user_id=api_key.user_id,
            channel_id=channel.id,
            model=request.model,
            status="error",
            tokens_input=input_tokens,
            tokens_output=0,
            cost=0,
            latency_ms=latency_ms,
            error_message=str(e),
        )
        
        logger.error(f"Chat completion error: {e}")
        raise UpstreamError(f"请求处理失败: {str(e)}")


async def stream_chat_completion(
    request: ChatCompletionRequest,
    api_key: APIKey,
    channel: Channel,
    upstream_model: str,
    input_tokens: int,
    start_time: float,
    db: AsyncSession,
) -> AsyncGenerator[str, None]:
    """流式聊天完成.
    
    Args:
        request: 请求
        api_key: API Key
        channel: 渠道
        upstream_model: 上游模型名称
        input_tokens: 输入token数
        start_time: 开始时间
        db: 数据库会话
        
    Yields:
        SSE格式的数据
    """
    config = channel.config
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:10]}"
    created = int(datetime.now(timezone.utc).timestamp())
    
    accumulated_content = ""
    output_tokens = 0
    latency_ms = 0
    error_occurred = False
    error_message = None
    
    try:
        # 构建上游请求
        upstream_request = {
            "model": upstream_model,
            "messages": [m.model_dump() for m in request.messages],
            "temperature": request.temperature,
            "stream": True,
        }
        
        if request.max_tokens:
            upstream_request["max_tokens"] = request.max_tokens
        
        # 发送流式请求
        async with httpx.AsyncClient(timeout=settings.UPSTREAM_TIMEOUT) as client:
            if channel.type == "openai":
                api_base = config.get("api_base", "https://api.openai.com")
                
                async with client.stream(
                    "POST",
                    f"{api_base}/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {config['api_key']}",
                        "Content-Type": "application/json",
                    },
                    json=upstream_request,
                ) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            
                            if data == "[DONE]":
                                break
                            
                            try:
                                chunk_data = json.loads(data)
                                
                                # 提取内容
                                delta = chunk_data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                
                                if content:
                                    accumulated_content += content
                                    output_tokens += count_tokens(content)
                                
                                # 构建并发送chunk
                                chunk = ChatCompletionChunk(
                                    id=completion_id,
                                    created=created,
                                    model=request.model,
                                    choices=[
                                        ChatCompletionChunkChoice(
                                            index=0,
                                            delta=delta,
                                            finish_reason=chunk_data["choices"][0].get("finish_reason"),
                                        )
                                    ],
                                )
                                
                                yield f"data: {chunk.model_dump_json()}\n\n"
                            
                            except json.JSONDecodeError:
                                continue
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        # 发送结束标记
        yield "data: [DONE]\n\n"
        
        # 计算费用
        cost = calculate_cost(request.model, input_tokens, output_tokens)
        
        # 记录日志
        await log_request(
            db=db,
            api_key_id=api_key.id,
            user_id=api_key.user_id,
            channel_id=channel.id,
            model=request.model,
            status="success",
            tokens_input=input_tokens,
            tokens_output=output_tokens,
            cost=cost,
            latency_ms=latency_ms,
        )
        
        # 更新API Key使用量
        api_key.budget_used = float(api_key.budget_used) + cost
        await db.commit()
    
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        error_occurred = True
        error_message = str(e)
        
        logger.error(f"Stream chat completion error: {e}")
        
        # 发送错误信息
        yield f'data: {{"error": {{"message": "{error_message}"}}}}\n\n'
        yield "data: [DONE]\n\n"
        
        # 记录错误日志
        await log_request(
            db=db,
            api_key_id=api_key.id,
            user_id=api_key.user_id,
            channel_id=channel.id,
            model=request.model,
            status="error",
            tokens_input=input_tokens,
            tokens_output=output_tokens,
            cost=0,
            latency_ms=latency_ms,
            error_message=error_message,
        )
