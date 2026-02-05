"""
认证接口测试
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.db.models.user import User


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient, db_session: AsyncSession):
    """测试用户注册"""
    user_data = {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "NewPass123!"
    }
    
    response = await client.post("/api/v1/auth/register", json=user_data)
    
    assert response.status_code == 201
    data = response.json()
    assert data["code"] == 201
    assert data["data"]["username"] == user_data["username"]
    assert data["data"]["email"] == user_data["email"]


@pytest.mark.asyncio
async def test_register_duplicate_username(client: AsyncClient, db_session: AsyncSession):
    """测试重复用户名注册"""
    # 先创建一个用户
    user = User(
        username="existinguser",
        email="existing@example.com",
        password_hash=get_password_hash("password123"),
        role="user",
        status="active"
    )
    db_session.add(user)
    await db_session.commit()
    
    # 尝试用相同的用户名注册
    user_data = {
        "username": "existinguser",
        "email": "new@example.com",
        "password": "NewPass123!"
    }
    
    response = await client.post("/api/v1/auth/register", json=user_data)
    
    assert response.status_code == 400
    data = response.json()
    assert data["code"] == 400


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, db_session: AsyncSession):
    """测试登录成功"""
    # 创建测试用户
    user = User(
        username="logintest",
        email="login@example.com",
        password_hash=get_password_hash("LoginPass123!"),
        role="user",
        status="active"
    )
    db_session.add(user)
    await db_session.commit()
    
    # 登录
    login_data = {
        "username": "logintest",
        "password": "LoginPass123!"
    }
    
    response = await client.post("/api/v1/auth/login", json=login_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert "access_token" in data["data"]
    assert data["data"]["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, db_session: AsyncSession):
    """测试密码错误"""
    # 创建测试用户
    user = User(
        username="wrongpasstest",
        email="wrongpass@example.com",
        password_hash=get_password_hash("CorrectPass123!"),
        role="user",
        status="active"
    )
    db_session.add(user)
    await db_session.commit()
    
    # 使用错误的密码登录
    login_data = {
        "username": "wrongpasstest",
        "password": "WrongPass123!"
    }
    
    response = await client.post("/api/v1/auth/login", json=login_data)
    
    assert response.status_code == 401
    data = response.json()
    assert data["code"] == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """测试不存在的用户登录"""
    login_data = {
        "username": "nonexistent",
        "password": "SomePass123!"
    }
    
    response = await client.post("/api/v1/auth/login", json=login_data)
    
    assert response.status_code == 401
    data = response.json()
    assert data["code"] == 401


@pytest.mark.asyncio
async def test_get_me_unauthorized(client: AsyncClient):
    """测试未授权访问用户信息"""
    response = await client.get("/api/v1/auth/me")
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_authorized(client: AsyncClient, db_session: AsyncSession):
    """测试已授权访问用户信息"""
    # 创建并登录用户
    user = User(
        username="meuser",
        email="me@example.com",
        password_hash=get_password_hash("MePass123!"),
        role="user",
        status="active"
    )
    db_session.add(user)
    await db_session.commit()
    
    # 登录获取token
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "meuser",
        "password": "MePass123!"
    })
    token = login_response.json()["data"]["access_token"]
    
    # 访问用户信息
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert data["data"]["username"] == "meuser"
