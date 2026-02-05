"""
用户相关模型单元测试
"""
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas.user import (
    User,
    UserBase,
    UserCreate,
    UserInDB,
    UserProfile,
    UserUpdate,
)


class TestUserBase:
    """用户基础模型测试"""

    def test_valid_user_base(self):
        """测试有效的用户基础数据"""
        user = UserBase(username="testuser", email="test@example.com")

        assert user.username == "testuser"
        assert user.email == "test@example.com"

    def test_username_min_length(self):
        """测试用户名最小长度"""
        with pytest.raises(ValidationError) as exc_info:
            UserBase(username="ab", email="test@example.com")

        assert "username" in str(exc_info.value)

    def test_username_max_length(self):
        """测试用户名最大长度"""
        with pytest.raises(ValidationError) as exc_info:
            UserBase(username="a" * 51, email="test@example.com")

        assert "username" in str(exc_info.value)

    def test_invalid_email(self):
        """测试无效邮箱"""
        with pytest.raises(ValidationError) as exc_info:
            UserBase(username="testuser", email="invalid-email")

        assert "email" in str(exc_info.value)

    def test_valid_username_boundary(self):
        """测试用户名边界值"""
        # 最小长度3
        user1 = UserBase(username="abc", email="test@example.com")
        assert user1.username == "abc"

        # 最大长度50
        user2 = UserBase(username="a" * 50, email="test@example.com")
        assert len(user2.username) == 50


class TestUserCreate:
    """用户创建模型测试"""

    def test_valid_user_create(self):
        """测试有效的用户创建数据"""
        user = UserCreate(
            username="newuser",
            email="new@example.com",
            password="SecurePass123!"
        )

        assert user.username == "newuser"
        assert user.email == "new@example.com"
        assert user.password == "SecurePass123!"

    def test_password_min_length(self):
        """测试密码最小长度"""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                username="testuser",
                email="test@example.com",
                password="12345"
            )

        assert "password" in str(exc_info.value)

    def test_password_max_length(self):
        """测试密码最大长度"""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                username="testuser",
                email="test@example.com",
                password="a" * 51
            )

        assert "password" in str(exc_info.value)

    def test_inherits_user_base(self):
        """测试继承UserBase"""
        user = UserCreate(
            username="testuser",
            email="test@example.com",
            password="password123"
        )

        assert isinstance(user, UserBase)

    def test_valid_password_boundary(self):
        """测试密码边界值"""
        # 最小长度6
        user1 = UserCreate(
            username="testuser",
            email="test@example.com",
            password="123456"
        )
        assert len(user1.password) == 6

        # 最大长度50
        user2 = UserCreate(
            username="testuser",
            email="test@example.com",
            password="a" * 50
        )
        assert len(user2.password) == 50


class TestUserUpdate:
    """用户更新模型测试"""

    def test_empty_update(self):
        """测试空更新"""
        update = UserUpdate()

        assert update.username is None
        assert update.email is None
        assert update.password is None
        assert update.is_active is None

    def test_partial_update(self):
        """测试部分更新"""
        update = UserUpdate(email="newemail@example.com")

        assert update.username is None
        assert update.email == "newemail@example.com"
        assert update.password is None

    def test_full_update(self):
        """测试完整更新"""
        update = UserUpdate(
            username="updateduser",
            email="updated@example.com",
            password="NewPass123!",
            is_active=False
        )

        assert update.username == "updateduser"
        assert update.email == "updated@example.com"
        assert update.password == "NewPass123!"
        assert update.is_active is False

    def test_update_username_validation(self):
        """测试更新用户名验证"""
        # 有效长度
        update1 = UserUpdate(username="validuser")
        assert update1.username == "validuser"

        # 太短
        with pytest.raises(ValidationError):
            UserUpdate(username="ab")

        # 太长
        with pytest.raises(ValidationError):
            UserUpdate(username="a" * 51)

    def test_update_password_validation(self):
        """测试更新密码验证"""
        # 有效长度
        update1 = UserUpdate(password="validpass123")
        assert update1.password == "validpass123"

        # 太短
        with pytest.raises(ValidationError):
            UserUpdate(password="12345")

        # 太长
        with pytest.raises(ValidationError):
            UserUpdate(password="a" * 51)


class TestUserInDB:
    """数据库用户模型测试"""

    def test_user_in_db_creation(self):
        """测试数据库用户创建"""
        now = datetime.utcnow()
        user = UserInDB(
            id=1,
            username="testuser",
            email="test@example.com",
            role="user",
            status="active",
            is_active=True,
            created_at=now,
            updated_at=now
        )

        assert user.id == 1
        assert user.username == "testuser"
        assert user.role == "user"
        assert user.status == "active"
        assert user.is_active is True

    def test_user_roles(self):
        """测试用户角色"""
        user_data = {
            "id": 1,
            "username": "testuser",
            "email": "test@example.com",
            "role": "admin",
            "status": "active",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        admin_user = UserInDB(**user_data)
        assert admin_user.role == "admin"

        user_data["role"] = "user"
        normal_user = UserInDB(**user_data)
        assert normal_user.role == "user"

    def test_user_status_values(self):
        """测试用户状态值"""
        now = datetime.utcnow()
        base_data = {
            "id": 1,
            "username": "testuser",
            "email": "test@example.com",
            "role": "user",
            "is_active": True,
            "created_at": now,
            "updated_at": now
        }

        # 活跃状态
        active_user = UserInDB(**{**base_data, "status": "active"})
        assert active_user.status == "active"

        # 非活跃状态
        inactive_user = UserInDB(**{**base_data, "status": "inactive"})
        assert inactive_user.status == "inactive"


class TestUser:
    """用户响应模型测试"""

    def test_user_response_creation(self):
        """测试用户响应创建"""
        user = User(
            id=1,
            username="testuser",
            email="test@example.com",
            role="user",
            status="active",
            created_at=datetime.utcnow()
        )

        assert user.id == 1
        assert user.username == "testuser"
        assert user.role == "user"

    def test_default_role_and_status(self):
        """测试默认角色和状态"""
        user = User(
            id=1,
            username="testuser",
            email="test@example.com",
            created_at=datetime.utcnow()
        )

        assert user.role == "user"
        assert user.status == "active"

    def test_optional_updated_at(self):
        """测试可选的更新时间"""
        now = datetime.utcnow()

        # 无更新时间
        user1 = User(
            id=1,
            username="testuser",
            email="test@example.com",
            created_at=now
        )
        assert user1.updated_at is None

        # 有更新时间
        user2 = User(
            id=1,
            username="testuser",
            email="test@example.com",
            created_at=now,
            updated_at=now
        )
        assert user2.updated_at is not None

    def test_inherits_user_base(self):
        """测试继承UserBase"""
        user = User(
            id=1,
            username="testuser",
            email="test@example.com",
            created_at=datetime.utcnow()
        )

        assert isinstance(user, UserBase)


class TestUserProfile:
    """用户个人资料模型测试"""

    def test_user_profile_creation(self):
        """测试用户资料创建"""
        profile = UserProfile(
            id=1,
            username="testuser",
            email="test@example.com",
            role="user",
            created_at=datetime.utcnow()
        )

        assert profile.id == 1
        assert profile.username == "testuser"
        assert profile.api_key_count == 0  # 默认值

    def test_custom_api_key_count(self):
        """测试自定义API Key数量"""
        profile = UserProfile(
            id=1,
            username="testuser",
            email="test@example.com",
            role="user",
            created_at=datetime.utcnow(),
            api_key_count=5
        )

        assert profile.api_key_count == 5

    def test_profile_fields(self):
        """测试资料字段"""
        now = datetime.utcnow()
        profile = UserProfile(
            id=1,
            username="testuser",
            email="test@example.com",
            role="user",
            created_at=now
        )

        assert hasattr(profile, 'id')
        assert hasattr(profile, 'username')
        assert hasattr(profile, 'email')
        assert hasattr(profile, 'role')
        assert hasattr(profile, 'created_at')
        assert hasattr(profile, 'api_key_count')


class TestModelSerialization:
    """模型序列化测试"""

    def test_user_create_serialization(self):
        """测试用户创建序列化"""
        user = UserCreate(
            username="testuser",
            email="test@example.com",
            password="password123"
        )

        json_data = user.model_dump()

        assert json_data["username"] == "testuser"
        assert json_data["email"] == "test@example.com"
        assert json_data["password"] == "password123"

    def test_user_response_serialization(self):
        """测试用户响应序列化"""
        now = datetime.utcnow()
        user = User(
            id=1,
            username="testuser",
            email="test@example.com",
            role="user",
            status="active",
            created_at=now
        )

        json_data = user.model_dump()

        assert json_data["id"] == 1
        assert json_data["role"] == "user"
        assert "created_at" in json_data

    def test_user_update_serialization(self):
        """测试用户更新序列化"""
        update = UserUpdate(email="new@example.com")

        json_data = update.model_dump()

        assert json_data["email"] == "new@example.com"
        assert json_data["username"] is None
        assert json_data["password"] is None


class TestEmailValidation:
    """邮箱验证测试"""

    def test_valid_emails(self):
        """测试有效邮箱"""
        valid_emails = [
            "user@example.com",
            "test.user@example.co.uk",
            "user+tag@example.com",
            "123@example.com",
            "user_name@example-domain.com",
        ]

        for email in valid_emails:
            user = UserBase(username="testuser", email=email)
            assert user.email == email

    def test_invalid_emails(self):
        """测试无效邮箱"""
        invalid_emails = [
            "plainaddress",
            "@missingusername.com",
            "user@.com",
            "user@domain",
            "user@domain..com",
            "",
        ]

        for email in invalid_emails:
            if email:  # 跳过空字符串，因为那是不同的验证
                with pytest.raises(ValidationError):
                    UserBase(username="testuser", email=email)
