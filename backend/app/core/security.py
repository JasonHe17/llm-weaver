"""
安全模块
提供密码加密、JWT token生成和验证功能
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Union

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.logging import logger

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT算法
ALGORITHM = "HS256"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码.
    
    Args:
        plain_password: 明文密码
        hashed_password: 哈希后的密码
        
    Returns:
        是否验证通过
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """获取密码哈希值.
    
    Args:
        password: 明文密码
        
    Returns:
        哈希后的密码
    """
    return pwd_context.hash(password)


def create_access_token(
    subject: Union[str, int],
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[dict] = None,
) -> str:
    """创建JWT访问令牌.
    
    Args:
        subject: 令牌主题（通常是用户ID）
        expires_delta: 过期时间增量
        extra_claims: 额外的声明数据
        
    Returns:
        JWT令牌字符串
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "access",
    }
    
    if extra_claims:
        to_encode.update(extra_claims)
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """解码并验证JWT令牌.
    
    Args:
        token: JWT令牌字符串
        
    Returns:
        解码后的payload，如果验证失败返回None
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"Token decode failed: {e}")
        return None


def generate_api_key() -> str:
    """生成新的API Key.
    
    Returns:
        格式为 sk-llmweaver-xxx 的API Key
    """
    import secrets
    import string
    
    # 生成32个字符的随机字符串
    alphabet = string.ascii_letters + string.digits
    random_part = "".join(secrets.choice(alphabet) for _ in range(32))
    
    return f"sk-llmweaver-{random_part}"


def hash_api_key(api_key: str) -> str:
    """对API Key进行哈希.
    
    Args:
        api_key: 原始API Key
        
    Returns:
        哈希后的API Key
    """
    return pwd_context.hash(api_key)


def verify_api_key(plain_api_key: str, hashed_api_key: str) -> bool:
    """验证API Key.
    
    Args:
        plain_api_key: 明文API Key
        hashed_api_key: 哈希后的API Key
        
    Returns:
        是否验证通过
    """
    return pwd_context.verify(plain_api_key, hashed_api_key)


def mask_api_key(api_key: str) -> str:
    """遮盖API Key，只显示前8位和后4位.
    
    Args:
        api_key: 原始API Key
        
    Returns:
        遮盖后的API Key，如 sk-llmwe...xxxx
    """
    if len(api_key) <= 12:
        return "*" * len(api_key)
    
    prefix = api_key[:12]  # sk-llmweaver-
    suffix = api_key[-4:]
    masked_length = len(api_key) - 16
    
    return f"{prefix}{'*' * masked_length}{suffix}"
