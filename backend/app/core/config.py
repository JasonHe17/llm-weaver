"""
应用配置管理
使用Pydantic Settings进行环境变量管理
"""

from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置类."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )
    
    # 项目信息
    PROJECT_NAME: str = "LLM Weaver"
    PROJECT_DESCRIPTION: str = "高性能LLM API中转服务平台"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # 安全设置
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ENCRYPTION_KEY: str = "your-encryption-key-32chars"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7天
    
    # 数据库设置
    DATABASE_URL: str = "postgresql://llm_weaver:secret@localhost:5432/llm_weaver"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 30
    
    # Redis设置
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_POOL_SIZE: int = 50
    
    # CORS设置
    CORS_ORIGINS: List[str] = ["http://localhost:8080", "http://localhost:5173"]
    CORS_ORIGIN_REGEX: Optional[str] = None
    
    # 日志设置
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # 限流设置
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # 请求超时
    REQUEST_TIMEOUT: int = 300
    
    # 上游API设置
    UPSTREAM_TIMEOUT: int = 120
    UPSTREAM_MAX_RETRIES: int = 3
    
    # 监控设置
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    
    @property
    def DATABASE_ASYNC_URL(self) -> str:
        """获取异步数据库URL."""
        return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    
    @property
    def is_development(self) -> bool:
        """是否为开发环境."""
        return self.LOG_LEVEL.upper() == "DEBUG"


# 全局配置实例
settings = Settings()
