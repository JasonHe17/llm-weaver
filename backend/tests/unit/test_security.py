"""
核心安全功能单元测试
"""
import pytest
from datetime import datetime, timedelta, timezone

from app.core.security import (
    create_access_token,
    verify_password,
    get_password_hash,
    generate_api_key,
    hash_api_key,
    mask_api_key,
)
from app.core.config import settings


class TestPasswordSecurity:
    """密码安全测试"""
    
    def test_password_hashing(self):
        """测试密码哈希"""
        password = "TestPassword123!"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("WrongPassword", hashed) is False
    
    def test_password_hashing_different_salts(self):
        """测试不同密码产生不同哈希"""
        password = "TestPassword123!"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # 相同的密码应该产生不同的哈希（因为盐不同）
        assert hash1 != hash2
        # 但都应该能验证通过
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestJWTToken:
    """JWT Token测试"""
    
    def test_create_access_token(self):
        """测试创建访问令牌"""
        user_id = 123
        token = create_access_token(user_id)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_create_access_token_with_data(self):
        """测试创建包含额外数据的令牌"""
        data = {"user_id": 123, "role": "admin"}
        token = create_access_token(data)
        
        assert token is not None
        assert isinstance(token, str)


class TestAPIKeySecurity:
    """API Key安全测试"""
    
    def test_generate_api_key(self):
        """测试生成API Key"""
        key = generate_api_key()
        
        assert key is not None
        assert isinstance(key, str)
        assert key.startswith("sk-")
        assert len(key) > 10
    
    def test_generate_api_key_unique(self):
        """测试生成的API Key是唯一的"""
        key1 = generate_api_key()
        key2 = generate_api_key()
        
        assert key1 != key2
    
    def test_hash_api_key(self):
        """测试API Key哈希"""
        key = "sk-testkey12345"
        hashed = hash_api_key(key)
        
        assert hashed is not None
        assert isinstance(hashed, str)
        assert len(hashed) > 0
    
    def test_mask_api_key(self):
        """测试API Key遮罩"""
        key_hash = "abcdefghijklmnop"
        masked = mask_api_key(key_hash)
        
        assert masked is not None
        assert "****" in masked
        assert masked.endswith("mnop")
    
    def test_hash_api_key_deterministic(self):
        """测试哈希是确定的"""
        key = "sk-testkey12345"
        hash1 = hash_api_key(key)
        hash2 = hash_api_key(key)
        
        # 相同的key应该产生相同的哈希
        assert hash1 == hash2


class TestConfig:
    """配置测试"""
    
    def test_secret_key_exists(self):
        """测试密钥存在"""
        assert settings.SECRET_KEY is not None
        assert len(settings.SECRET_KEY) > 0
    
    def test_encryption_key_exists(self):
        """测试加密密钥存在"""
        assert settings.ENCRYPTION_KEY is not None
        assert len(settings.ENCRYPTION_KEY) > 0
