"""
核心配置单元测试
"""
import os
from unittest.mock import patch

import pytest
from pydantic_settings import SettingsConfigDict

from app.core.config import Settings, settings


class TestSettings:
    """Settings配置类测试"""

    def test_default_values(self):
        """测试默认配置值"""
        test_settings = Settings()

        assert test_settings.PROJECT_NAME == "LLM Weaver"
        assert test_settings.PROJECT_DESCRIPTION == "高性能LLM API中转服务平台"
        assert test_settings.VERSION == "1.0.0"
        assert test_settings.API_V1_STR == "/api/v1"

    def test_security_defaults(self):
        """测试安全配置默认值"""
        test_settings = Settings()

        assert test_settings.SECRET_KEY == "your-secret-key-change-in-production"
        assert test_settings.ENCRYPTION_KEY == "your-encryption-key-32chars"
        assert test_settings.ACCESS_TOKEN_EXPIRE_MINUTES == 60 * 24 * 7  # 7天

    def test_database_defaults(self):
        """测试数据库配置默认值"""
        test_settings = Settings()

        assert "postgresql://" in test_settings.DATABASE_URL
        assert test_settings.DATABASE_POOL_SIZE == 20
        assert test_settings.DATABASE_MAX_OVERFLOW == 30

    def test_redis_defaults(self):
        """测试Redis配置默认值"""
        test_settings = Settings()

        assert test_settings.REDIS_URL == "redis://localhost:6379/0"
        assert test_settings.REDIS_POOL_SIZE == 50

    def test_cors_defaults(self):
        """测试CORS配置默认值"""
        test_settings = Settings()

        assert "http://localhost:8080" in test_settings.CORS_ORIGINS
        assert "http://localhost:5173" in test_settings.CORS_ORIGINS
        assert test_settings.CORS_ORIGIN_REGEX is None

    def test_logging_defaults(self):
        """测试日志配置默认值"""
        test_settings = Settings()

        assert test_settings.LOG_LEVEL == "INFO"
        assert test_settings.LOG_FORMAT == "json"

    def test_rate_limit_defaults(self):
        """测试限流配置默认值"""
        test_settings = Settings()

        assert test_settings.RATE_LIMIT_PER_MINUTE == 60

    def test_timeout_defaults(self):
        """测试超时配置默认值"""
        test_settings = Settings()

        assert test_settings.REQUEST_TIMEOUT == 300
        assert test_settings.UPSTREAM_TIMEOUT == 120
        assert test_settings.UPSTREAM_MAX_RETRIES == 3

    def test_metrics_defaults(self):
        """测试监控配置默认值"""
        test_settings = Settings()

        assert test_settings.ENABLE_METRICS is True
        assert test_settings.METRICS_PORT == 9090

    def test_database_async_url_property(self):
        """测试DATABASE_ASYNC_URL属性"""
        test_settings = Settings()
        test_settings.DATABASE_URL = "postgresql://user:pass@localhost:5432/db"

        async_url = test_settings.DATABASE_ASYNC_URL

        assert "postgresql+asyncpg://" in async_url
        assert "user:pass@localhost:5432/db" in async_url

    def test_is_development_property(self):
        """测试is_development属性"""
        # DEBUG级别应该返回True
        dev_settings = Settings()
        dev_settings.LOG_LEVEL = "DEBUG"
        assert dev_settings.is_development is True

        # INFO级别应该返回False
        prod_settings = Settings()
        prod_settings.LOG_LEVEL = "INFO"
        assert prod_settings.is_development is False

        # WARNING级别应该返回False
        prod_settings.LOG_LEVEL = "WARNING"
        assert prod_settings.is_development is False

    def test_environment_variables(self):
        """测试环境变量加载"""
        with patch.dict(os.environ, {
            "PROJECT_NAME": "Test Project",
            "SECRET_KEY": "test-secret-key",
            "DATABASE_URL": "postgresql://test:test@localhost/test",
            "LOG_LEVEL": "DEBUG"
        }, clear=False):
            test_settings = Settings()
            assert test_settings.PROJECT_NAME == "Test Project"
            assert test_settings.SECRET_KEY == "test-secret-key"
            assert test_settings.DATABASE_URL == "postgresql://test:test@localhost/test"
            assert test_settings.LOG_LEVEL == "DEBUG"

    def test_global_settings_instance(self):
        """测试全局settings实例"""
        assert isinstance(settings, Settings)
        assert settings.PROJECT_NAME is not None


class TestSettingsModelConfig:
    """Settings模型配置测试"""

    def test_model_config(self):
        """测试模型配置"""
        test_settings = Settings()

        assert test_settings.model_config is not None
        # 验证配置使用.env文件
        assert hasattr(test_settings, 'model_config')


class TestSettingsEdgeCases:
    """Settings边界情况测试"""

    def test_empty_cors_origins(self):
        """测试空CORS来源列表"""
        test_settings = Settings()
        test_settings.CORS_ORIGINS = []
        assert test_settings.CORS_ORIGINS == []

    def test_custom_cors_origins(self):
        """测试自定义CORS来源"""
        test_settings = Settings()
        test_settings.CORS_ORIGINS = ["https://example.com", "https://app.example.com"]
        assert len(test_settings.CORS_ORIGINS) == 2
        assert "https://example.com" in test_settings.CORS_ORIGINS

    def test_token_expire_boundary(self):
        """测试token过期时间边界值"""
        test_settings = Settings()
        # 测试0值
        test_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 0
        assert test_settings.ACCESS_TOKEN_EXPIRE_MINUTES == 0
        # 测试极大值
        test_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 999999
        assert test_settings.ACCESS_TOKEN_EXPIRE_MINUTES == 999999
