"""
API Keys接口测试
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.db.models.user import User


@pytest.fixture
async def auth_token(client: AsyncClient, db_session: AsyncSession) -> str:
    """创建测试用户并返回token"""
    user = User(
        username="apikeyuser",
        email="apikey@example.com",
        password_hash=get_password_hash("TestPass123!"),
        role="user",
        status="active"
    )
    db_session.add(user)
    await db_session.commit()
    
    response = await client.post("/api/v1/auth/login", json={
        "username": "apikeyuser",
        "password": "TestPass123!"
    })
    return response.json()["data"]["access_token"]


@pytest.mark.asyncio
async def test_create_api_key(client: AsyncClient, auth_token: str):
    """测试创建API Key"""
    api_key_data = {
        "name": "Test API Key",
        "budget_limit": 100.0,
        "rate_limit": 60
    }
    
    response = await client.post(
        "/api/v1/api-keys",
        json=api_key_data,
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["code"] == 201
    assert data["data"]["name"] == api_key_data["name"]
    assert "key" in data["data"]  # 创建时返回完整key


@pytest.mark.asyncio
async def test_list_api_keys(client: AsyncClient, auth_token: str):
    """测试获取API Key列表"""
    # 先创建一个API Key
    await client.post(
        "/api/v1/api-keys",
        json={"name": "Test Key 1", "rate_limit": 60},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    response = await client.get(
        "/api/v1/api-keys",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert "items" in data["data"]
    assert len(data["data"]["items"]) >= 1


@pytest.mark.asyncio
async def test_update_api_key(client: AsyncClient, auth_token: str):
    """测试更新API Key"""
    # 先创建API Key
    create_response = await client.post(
        "/api/v1/api-keys",
        json={"name": "Key To Update", "rate_limit": 60},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    key_id = create_response.json()["data"]["id"]
    
    # 更新
    update_data = {
        "name": "Updated Key Name",
        "status": "inactive"
    }
    
    response = await client.put(
        f"/api/v1/api-keys/{key_id}",
        json=update_data,
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert data["data"]["name"] == update_data["name"]
    assert data["data"]["status"] == update_data["status"]


@pytest.mark.asyncio
async def test_delete_api_key(client: AsyncClient, auth_token: str):
    """测试删除API Key"""
    # 先创建API Key
    create_response = await client.post(
        "/api/v1/api-keys",
        json={"name": "Key To Delete", "rate_limit": 60},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    key_id = create_response.json()["data"]["id"]
    
    # 删除
    response = await client.delete(
        f"/api/v1/api-keys/{key_id}",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200


@pytest.mark.asyncio
async def test_api_key_unauthorized(client: AsyncClient):
    """测试未授权访问"""
    response = await client.get("/api/v1/api-keys")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_api_key_invalid_token(client: AsyncClient):
    """测试无效token"""
    response = await client.get(
        "/api/v1/api-keys",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401
