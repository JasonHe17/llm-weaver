"""
自定义异常类单元测试
"""
import pytest

from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    BusinessError,
    InsufficientBalanceError,
    NotFoundError,
    RateLimitError,
    UpstreamError,
    ValidationError,
)


class TestBusinessError:
    """业务异常基类测试"""

    def test_basic_error(self):
        """测试基本错误创建"""
        error = BusinessError("Something went wrong")

        assert error.message == "Something went wrong"
        assert error.code == 400
        assert error.status_code == 400
        assert str(error) == "Something went wrong"

    def test_custom_code(self):
        """测试自定义错误码"""
        error = BusinessError("Custom error", code=500, status_code=500)

        assert error.code == 500
        assert error.status_code == 500

    def test_error_inheritance(self):
        """测试错误继承"""
        error = BusinessError("Base error")
        assert isinstance(error, Exception)


class TestAuthenticationError:
    """认证错误测试"""

    def test_default_message(self):
        """测试默认错误消息"""
        error = AuthenticationError()

        assert error.message == "Authentication failed"
        assert error.code == 401
        assert error.status_code == 401

    def test_custom_message(self):
        """测试自定义错误消息"""
        error = AuthenticationError("Invalid token")

        assert error.message == "Invalid token"
        assert error.code == 401

    def test_inheritance(self):
        """测试继承关系"""
        error = AuthenticationError()
        assert isinstance(error, BusinessError)


class TestAuthorizationError:
    """授权错误测试"""

    def test_default_message(self):
        """测试默认错误消息"""
        error = AuthorizationError()

        assert error.message == "Permission denied"
        assert error.code == 403
        assert error.status_code == 403

    def test_custom_message(self):
        """测试自定义错误消息"""
        error = AuthorizationError("Admin access required")

        assert error.message == "Admin access required"

    def test_inheritance(self):
        """测试继承关系"""
        error = AuthorizationError()
        assert isinstance(error, BusinessError)


class TestNotFoundError:
    """资源不存在错误测试"""

    def test_default_message(self):
        """测试默认错误消息"""
        error = NotFoundError()

        assert error.message == "Resource not found"
        assert error.code == 404
        assert error.status_code == 404

    def test_custom_message(self):
        """测试自定义错误消息"""
        error = NotFoundError("User 123 not found")

        assert error.message == "User 123 not found"

    def test_inheritance(self):
        """测试继承关系"""
        error = NotFoundError()
        assert isinstance(error, BusinessError)


class TestRateLimitError:
    """限流错误测试"""

    def test_default_message(self):
        """测试默认错误消息"""
        error = RateLimitError()

        assert error.message == "Rate limit exceeded"
        assert error.code == 429
        assert error.status_code == 429

    def test_custom_message(self):
        """测试自定义错误消息"""
        error = RateLimitError("Too many requests, try again later")

        assert error.message == "Too many requests, try again later"

    def test_inheritance(self):
        """测试继承关系"""
        error = RateLimitError()
        assert isinstance(error, BusinessError)


class TestUpstreamError:
    """上游服务错误测试"""

    def test_default_message(self):
        """测试默认错误消息"""
        error = UpstreamError()

        assert error.message == "Upstream service error"
        assert error.code == 502
        assert error.status_code == 502

    def test_custom_message(self):
        """测试自定义错误消息"""
        error = UpstreamError("OpenAI API unavailable")

        assert error.message == "OpenAI API unavailable"

    def test_inheritance(self):
        """测试继承关系"""
        error = UpstreamError()
        assert isinstance(error, BusinessError)


class TestValidationError:
    """数据验证错误测试"""

    def test_default_message(self):
        """测试默认错误消息"""
        error = ValidationError()

        assert error.message == "Validation error"
        assert error.code == 400
        assert error.status_code == 400

    def test_custom_message(self):
        """测试自定义错误消息"""
        error = ValidationError("Invalid email format")

        assert error.message == "Invalid email format"

    def test_inheritance(self):
        """测试继承关系"""
        error = ValidationError()
        assert isinstance(error, BusinessError)


class TestInsufficientBalanceError:
    """余额不足错误测试"""

    def test_default_message(self):
        """测试默认错误消息"""
        error = InsufficientBalanceError()

        assert error.message == "Insufficient balance"
        assert error.code == 402
        assert error.status_code == 402

    def test_custom_message(self):
        """测试自定义错误消息"""
        error = InsufficientBalanceError("Your balance is too low")

        assert error.message == "Your balance is too low"

    def test_inheritance(self):
        """测试继承关系"""
        error = InsufficientBalanceError()
        assert isinstance(error, BusinessError)


class TestExceptionRaising:
    """异常抛出测试"""

    def test_raise_authentication_error(self):
        """测试抛出认证错误"""
        with pytest.raises(AuthenticationError) as exc_info:
            raise AuthenticationError("Login required")

        assert exc_info.value.code == 401

    def test_raise_not_found_error(self):
        """测试抛出资源不存在错误"""
        with pytest.raises(NotFoundError) as exc_info:
            raise NotFoundError("API key not found")

        assert exc_info.value.code == 404

    def test_catch_as_business_error(self):
        """测试作为BusinessError捕获"""
        errors = [
            AuthenticationError(),
            AuthorizationError(),
            NotFoundError(),
            RateLimitError(),
            UpstreamError(),
            ValidationError(),
            InsufficientBalanceError(),
        ]

        for error in errors:
            try:
                raise error
            except BusinessError as e:
                assert hasattr(e, 'code')
                assert hasattr(e, 'status_code')
                assert hasattr(e, 'message')


class TestErrorHierarchy:
    """错误层次结构测试"""

    def test_all_inherit_from_business(self):
        """测试所有错误都继承自BusinessError"""
        error_classes = [
            AuthenticationError,
            AuthorizationError,
            NotFoundError,
            RateLimitError,
            UpstreamError,
            ValidationError,
            InsufficientBalanceError,
        ]

        for error_class in error_classes:
            error = error_class()
            assert isinstance(error, BusinessError)
            assert isinstance(error, Exception)

    def test_status_code_consistency(self):
        """测试状态码一致性"""
        test_cases = [
            (AuthenticationError, 401),
            (AuthorizationError, 403),
            (NotFoundError, 404),
            (RateLimitError, 429),
            (UpstreamError, 502),
            (ValidationError, 400),
            (InsufficientBalanceError, 402),
        ]

        for error_class, expected_code in test_cases:
            error = error_class()
            assert error.code == expected_code
            assert error.status_code == expected_code
