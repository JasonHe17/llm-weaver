"""
LLM Weaver - API中转服务
FastAPI应用主入口

本服务提供高性能的LLM API聚合和转发能力，支持多供应商渠道管理、API Key管理、用量统计等功能。
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router, openai_router
from app.api.v1.health import router as health_router
from app.core.config import settings
from app.core.exceptions import BusinessError
from app.core.logging import logger
from app.db.session import init_db


def custom_openapi():
    """自定义OpenAPI配置，添加安全方案和扩展信息."""
    if app.openapi_schema:
        return app.openapi_schema
    
    from fastapi.openapi.utils import get_openapi
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # 添加安全方案
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "使用JWT Bearer Token进行认证。格式：`Bearer <token>`",
        },
        "apiKeyAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "API Key",
            "description": "使用API Key进行认证。格式：`Bearer <api_key>`",
        },
    }
    
    # 添加全局安全要求
    openapi_schema["security"] = [{"bearerAuth": []}]
    
    # 添加扩展信息
    openapi_schema["info"]["x-logo"] = {
        "url": "https://cdn.jsdelivr.net/gh/simple-icons/simple-icons/icons/openai.svg",
        "backgroundColor": "#fafafa",
        "altText": "LLM Weaver Logo",
    }
    
    # 添加联系方式
    openapi_schema["info"]["contact"] = {
        "name": "LLM Weaver Team",
        "email": "support@llmweaver.dev",
    }
    
    # 添加许可证
    openapi_schema["info"]["license"] = {
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    }
    
    # 添加外部文档
    openapi_schema["externalDocs"] = {
        "description": "查看完整的API文档",
        "url": f"{settings.API_V1_STR}/docs",
    }
    
    # 添加标签描述
    openapi_schema["tags"] = [
        {
            "name": "health",
            "description": "健康检查和系统状态",
            "externalDocs": {
                "description": "了解更多",
                "url": "https://docs.llmweaver.dev/health",
            },
        },
        {
            "name": "auth",
            "description": "用户认证相关接口",
            "externalDocs": {
                "description": "认证指南",
                "url": "https://docs.llmweaver.dev/auth",
            },
        },
        {
            "name": "api-keys",
            "description": "API Key管理接口。API Key用于OpenAI兼容接口的调用认证",
        },
        {
            "name": "channels",
            "description": "上游供应商渠道管理接口。支持OpenAI、Anthropic、Azure等多种供应商",
        },
        {
            "name": "models",
            "description": "可用模型管理接口",
        },
        {
            "name": "usage",
            "description": "用量统计和请求日志接口",
        },
        {
            "name": "openai-compatible",
            "description": "OpenAI兼容接口。支持 `/v1/models` 和 `/v1/chat/completions`",
        },
    ]
    
    # 添加服务器信息
    openapi_schema["servers"] = [
        {
            "url": "http://localhost:8000",
            "description": "本地开发服务器",
        },
        {
            "url": "{protocol}://{host}",
            "description": "自定义服务器",
            "variables": {
                "protocol": {
                    "enum": ["http", "https"],
                    "default": "https",
                    "description": "协议类型",
                },
                "host": {
                    "default": "api.llmweaver.dev",
                    "description": "服务器地址",
                },
            },
        },
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


# 标签描述
TAGS_METADATA = [
    {
        "name": "health",
        "description": "健康检查和系统状态监控",
    },
    {
        "name": "auth",
        "description": "用户认证相关接口，包括登录、注册、Token刷新等",
    },
    {
        "name": "api-keys",
        "description": "API Key管理接口，用于创建和管理API Key以调用OpenAI兼容接口",
    },
    {
        "name": "channels",
        "description": "上游供应商渠道管理接口，支持OpenAI、Anthropic、Azure等",
    },
    {
        "name": "models",
        "description": "可用模型查询接口",
    },
    {
        "name": "usage",
        "description": "用量统计和请求日志查询接口",
    },
    {
        "name": "openai-compatible",
        "description": "OpenAI API兼容接口，支持 `/v1/models` 和 `/v1/chat/completions`",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理器."""
    # 启动时
    logger.info("Starting LLM Weaver...")
    await init_db()
    logger.info("Database initialized")
    
    yield
    
    # 关闭时
    logger.info("Shutting down LLM Weaver...")


# 创建FastAPI应用
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
    openapi_tags=TAGS_METADATA,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# 设置自定义OpenAPI
app.openapi = custom_openapi

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录请求日志和耗时."""
    import time
    
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path}",
        status_code=response.status_code,
        process_time=f"{process_time:.3f}s",
        client_ip=request.client.host if request.client else None,
    )
    
    response.headers["X-Process-Time"] = str(process_time)
    return response


# 业务异常处理器
@app.exception_handler(BusinessError)
async def business_exception_handler(request: Request, exc: BusinessError):
    """处理业务异常."""
    logger.warning(f"Business error: {exc.message}", code=exc.code)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "data": None,
        },
    )


# 通用异常处理器
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """处理通用异常."""
    logger.exception("Unexpected error occurred")
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "message": "Internal server error",
            "data": None,
        },
    )


# 注册路由
# 健康检查
app.include_router(health_router, prefix="/api/v1", tags=["health"])

# 原生API路由
app.include_router(api_router, prefix=settings.API_V1_STR)

# OpenAI兼容接口（挂载在 /v1 路径下）
app.include_router(openai_router, prefix="/v1")


@app.get("/")
async def root():
    """根路径重定向到文档."""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "description": settings.PROJECT_DESCRIPTION,
        "documentation": {
            "swagger": f"{settings.API_V1_STR}/docs",
            "redoc": f"{settings.API_V1_STR}/redoc",
            "openapi": f"{settings.API_V1_STR}/openapi.json",
        },
        "endpoints": {
            "health": "/health",
            "api_v1": settings.API_V1_STR,
            "openai_compatible": "/v1",
        },
    }


@app.get("/health")
async def simple_health():
    """简单健康检查端点."""
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
