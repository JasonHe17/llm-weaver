"""
Pytest配置和共享fixture
"""
import asyncio
import os
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# 设置测试环境
os.environ["TESTING"] = "true"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test_db"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["ENCRYPTION_KEY"] = "test-encryption-key-32-chars"

from app.main import app
from app.db.base import Base
from app.db.session import get_db


# 创建测试引擎
TEST_DATABASE_URL = "postgresql+asyncpg://test:test@localhost:5432/test_db"
engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    """创建数据库引擎并初始化表结构"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """创建数据库会话"""
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """创建测试客户端"""
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    del app.dependency_overrides[get_db]


@pytest.fixture
def test_user_data():
    """测试用户数据"""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPass123!"
    }


@pytest.fixture
def test_api_key_data():
    """测试API Key数据"""
    return {
        "name": "Test API Key",
        "budget_limit": 100.0,
        "rate_limit": 60,
        "allowed_models": ["gpt-3.5-turbo"]
    }


@pytest.fixture
def test_channel_data():
    """测试渠道数据"""
    return {
        "name": "Test Channel",
        "type": "openai",
        "config": {
            "api_key": "sk-test123",
            "api_base": "https://api.openai.com"
        },
        "weight": 100,
        "priority": 1,
        "models": [
            {"model_id": "gpt-3.5-turbo", "mapped_model": "gpt-3.5-turbo"}
        ]
    }
