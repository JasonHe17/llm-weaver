"""
自定义异常类
"""


class BusinessError(Exception):
    """业务异常基类."""
    
    def __init__(
        self,
        message: str,
        code: int = 400,
        status_code: int = 400,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)


class AuthenticationError(BusinessError):
    """认证错误."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, code=401, status_code=401)


class AuthorizationError(BusinessError):
    """授权错误."""
    
    def __init__(self, message: str = "Permission denied"):
        super().__init__(message, code=403, status_code=403)


class NotFoundError(BusinessError):
    """资源不存在."""
    
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, code=404, status_code=404)


class RateLimitError(BusinessError):
    """限流错误."""
    
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, code=429, status_code=429)


class UpstreamError(BusinessError):
    """上游服务错误."""
    
    def __init__(self, message: str = "Upstream service error"):
        super().__init__(message, code=502, status_code=502)


class ValidationError(BusinessError):
    """数据验证错误."""
    
    def __init__(self, message: str = "Validation error"):
        super().__init__(message, code=400, status_code=400)


class InsufficientBalanceError(BusinessError):
    """余额不足."""
    
    def __init__(self, message: str = "Insufficient balance"):
        super().__init__(message, code=402, status_code=402)
