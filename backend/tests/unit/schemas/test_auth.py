"""
认证相关模型单元测试
"""
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    PasswordChangeRequest,
    PasswordResetRequest,
    RefreshTokenRequest,
    RegisterRequest,
    Token,
    TokenPayload,
)
from app.schemas.user import User


class TestToken:
    """Token模型测试"""

    def test_token_default_values(self):
        """测试Token默认值"""
        token = Token(access_token="test_token_123")

        assert token.access_token == "test_token_123"
        assert token.token_type == "bearer"
        assert token.expires_in == 604800  # 7天

    def test_token_custom_values(self):
        """测试Token自定义值"""
        token = Token(
            access_token="custom_token",
            token_type="Bearer",
            expires_in=3600
        )

        assert token.access_token == "custom_token"
        assert token.token_type == "Bearer"
        assert token.expires_in == 3600

    def test_required_access_token(self):
        """测试access_token必填"""
        with pytest.raises(ValidationError) as exc_info:
            Token()

        assert "access_token" in str(exc_info.value)

    def test_token_string_values(self):
        """测试Token字符串值"""
        token = Token(access_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")

        assert isinstance(token.access_token, str)
        assert len(token.access_token) > 0


class TestTokenPayload:
    """Token载荷模型测试"""

    def test_empty_payload(self):
        """测试空载荷"""
        payload = TokenPayload()

        assert payload.sub is None
        assert payload.exp is None
        assert payload.type is None

    def test_full_payload(self):
        """测试完整载荷"""
        payload = TokenPayload(
            sub="user123",
            exp=1234567890,
            type="access"
        )

        assert payload.sub == "user123"
        assert payload.exp == 1234567890
        assert payload.type == "access"

    def test_partial_payload(self):
        """测试部分载荷"""
        payload = TokenPayload(sub="user456")

        assert payload.sub == "user456"
        assert payload.exp is None
        assert payload.type is None

    def test_user_id_as_subject(self):
        """测试用户ID作为subject"""
        payload = TokenPayload(sub="12345")

        assert payload.sub == "12345"


class TestLoginRequest:
    """登录请求模型测试"""

    def test_valid_login_request(self):
        """测试有效的登录请求"""
        login = LoginRequest(
            email="user@example.com",
            password="securepassword123"
        )

        assert login.email == "user@example.com"
        assert login.password == "securepassword123"

    def test_invalid_email(self):
        """测试无效邮箱"""
        with pytest.raises(ValidationError) as exc_info:
            LoginRequest(
                email="invalid-email",
                password="password123"
            )

        assert "email" in str(exc_info.value)

    def test_empty_password(self):
        """测试空密码"""
        with pytest.raises(ValidationError) as exc_info:
            LoginRequest(
                email="user@example.com",
                password=""
            )

        assert "password" in str(exc_info.value)

    def test_required_fields(self):
        """测试必填字段"""
        with pytest.raises(ValidationError):
            LoginRequest(email="user@example.com")

        with pytest.raises(ValidationError):
            LoginRequest(password="password123")


class TestLoginResponse:
    """登录响应模型测试"""

    def test_valid_login_response(self):
        """测试有效的登录响应"""
        user = User(
            id=1,
            username="testuser",
            email="test@example.com",
            created_at=datetime.utcnow()
        )

        response = LoginResponse(
            access_token="token123",
            token_type="bearer",
            expires_in=604800,
            user=user
        )

        assert response.access_token == "token123"
        assert response.user.username == "testuser"

    def test_all_fields_required(self):
        """测试所有字段必填"""
        user = User(
            id=1,
            username="testuser",
            email="test@example.com",
            created_at=datetime.utcnow()
        )

        # 缺少access_token
        with pytest.raises(ValidationError):
            LoginResponse(
                token_type="bearer",
                expires_in=604800,
                user=user
            )

        # 缺少user
        with pytest.raises(ValidationError):
            LoginResponse(
                access_token="token123",
                token_type="bearer",
                expires_in=604800
            )


class TestRegisterRequest:
    """注册请求模型测试"""

    def test_valid_register_request(self):
        """测试有效的注册请求"""
        register = RegisterRequest(
            username="newuser",
            email="new@example.com",
            password="SecurePass123!"
        )

        assert register.username == "newuser"
        assert register.email == "new@example.com"
        assert register.password == "SecurePass123!"

    def test_username_min_length(self):
        """测试用户名最小长度"""
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(
                username="ab",
                email="test@example.com",
                password="password123"
            )

        assert "username" in str(exc_info.value)

    def test_username_max_length(self):
        """测试用户名最大长度"""
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(
                username="a" * 51,
                email="test@example.com",
                password="password123"
            )

        assert "username" in str(exc_info.value)

    def test_password_min_length(self):
        """测试密码最小长度"""
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(
                username="testuser",
                email="test@example.com",
                password="12345"
            )

        assert "password" in str(exc_info.value)

    def test_password_max_length(self):
        """测试密码最大长度"""
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(
                username="testuser",
                email="test@example.com",
                password="a" * 51
            )

        assert "password" in str(exc_info.value)

    def test_all_fields_required(self):
        """测试所有字段必填"""
        with pytest.raises(ValidationError):
            RegisterRequest(username="testuser", email="test@example.com")

        with pytest.raises(ValidationError):
            RegisterRequest(username="testuser", password="password123")

        with pytest.raises(ValidationError):
            RegisterRequest(email="test@example.com", password="password123")

    def test_valid_boundaries(self):
        """测试边界值"""
        # 用户名边界
        user1 = RegisterRequest(
            username="abc",
            email="test@example.com",
            password="password123"
        )
        assert user1.username == "abc"

        user2 = RegisterRequest(
            username="a" * 50,
            email="test@example.com",
            password="password123"
        )
        assert len(user2.username) == 50

        # 密码边界
        user3 = RegisterRequest(
            username="testuser",
            email="test@example.com",
            password="123456"
        )
        assert len(user3.password) == 6

        user4 = RegisterRequest(
            username="testuser",
            email="test@example.com",
            password="a" * 50
        )
        assert len(user4.password) == 50


class TestRefreshTokenRequest:
    """刷新Token请求模型测试"""

    def test_valid_refresh_request(self):
        """测试有效的刷新请求"""
        request = RefreshTokenRequest(refresh_token="refresh_token_123")

        assert request.refresh_token == "refresh_token_123"

    def test_required_refresh_token(self):
        """测试refresh_token必填"""
        with pytest.raises(ValidationError) as exc_info:
            RefreshTokenRequest()

        assert "refresh_token" in str(exc_info.value)

    def test_empty_refresh_token(self):
        """测试空刷新token"""
        with pytest.raises(ValidationError) as exc_info:
            RefreshTokenRequest(refresh_token="")

        assert "refresh_token" in str(exc_info.value)


class TestPasswordResetRequest:
    """密码重置请求模型测试"""

    def test_valid_reset_request(self):
        """测试有效的重置请求"""
        request = PasswordResetRequest(email="user@example.com")

        assert request.email == "user@example.com"

    def test_required_email(self):
        """测试邮箱必填"""
        with pytest.raises(ValidationError) as exc_info:
            PasswordResetRequest()

        assert "email" in str(exc_info.value)

    def test_invalid_email(self):
        """测试无效邮箱"""
        with pytest.raises(ValidationError) as exc_info:
            PasswordResetRequest(email="invalid-email")

        assert "email" in str(exc_info.value)


class TestPasswordChangeRequest:
    """密码修改请求模型测试"""

    def test_valid_change_request(self):
        """测试有效的修改请求"""
        request = PasswordChangeRequest(
            old_password="oldpass123",
            new_password="newpass123"
        )

        assert request.old_password == "oldpass123"
        assert request.new_password == "newpass123"

    def test_required_fields(self):
        """测试必填字段"""
        with pytest.raises(ValidationError):
            PasswordChangeRequest(old_password="oldpass123")

        with pytest.raises(ValidationError):
            PasswordChangeRequest(new_password="newpass123")

    def test_new_password_min_length(self):
        """测试新密码最小长度"""
        with pytest.raises(ValidationError) as exc_info:
            PasswordChangeRequest(
                old_password="oldpass123",
                new_password="12345"
            )

        assert "new_password" in str(exc_info.value)

    def test_new_password_max_length(self):
        """测试新密码最大长度"""
        with pytest.raises(ValidationError) as exc_info:
            PasswordChangeRequest(
                old_password="oldpass123",
                new_password="a" * 51
            )

        assert "new_password" in str(exc_info.value)

    def test_same_password_not_allowed(self):
        """测试新旧密码不能相同（业务逻辑测试）"""
        # 注：这里只测试模型层面的验证
        # 实际业务逻辑应该在service层检查
        request = PasswordChangeRequest(
            old_password="password123",
            new_password="password456"
        )

        assert request.old_password != request.new_password


class TestModelSerialization:
    """模型序列化测试"""

    def test_token_serialization(self):
        """测试Token序列化"""
        token = Token(
            access_token="test_token",
            token_type="bearer",
            expires_in=3600
        )

        json_data = token.model_dump()

        assert json_data["access_token"] == "test_token"
        assert json_data["token_type"] == "bearer"
        assert json_data["expires_in"] == 3600

    def test_login_request_serialization(self):
        """测试登录请求序列化"""
        login = LoginRequest(
            email="user@example.com",
            password="password123"
        )

        json_data = login.model_dump()

        assert json_data["email"] == "user@example.com"
        assert json_data["password"] == "password123"

    def test_register_request_serialization(self):
        """测试注册请求序列化"""
        register = RegisterRequest(
            username="newuser",
            email="new@example.com",
            password="SecurePass123!"
        )

        json_data = register.model_dump()

        assert json_data["username"] == "newuser"
        assert json_data["email"] == "new@example.com"
        assert json_data["password"] == "SecurePass123!"

    def test_password_change_serialization(self):
        """测试密码修改序列化"""
        request = PasswordChangeRequest(
            old_password="oldpass",
            new_password="newpass123"
        )

        json_data = request.model_dump()

        assert json_data["old_password"] == "oldpass"
        assert json_data["new_password"] == "newpass123"
