"""
健康检查接口测试
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """测试健康检查端点"""
    response = await client.get("/api/v1/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert "data" in data
    assert data["data"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_check_response_format(client: AsyncClient):
    """测试健康检查响应格式"""
    response = await client.get("/api/v1/health")
    
    assert response.status_code == 200
    data = response.json()
    
    # 检查必需的字段
    assert "code" in data
    assert "message" in data
    assert "data" in data
    
    # 检查data字段
    assert "status" in data["data"]
    assert "version" in data["data"]
    assert "timestamp" in data["data"]
