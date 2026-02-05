"""
通用响应模型单元测试
"""
import pytest
from pydantic import ValidationError

from app.schemas.common import (
    ErrorResponse,
    PaginatedResponse,
    PaginationParams,
    ResponseModel,
)


class TestResponseModel:
    """通用响应模型测试"""

    def test_default_values(self):
        """测试默认值"""
        response = ResponseModel()

        assert response.code == 200
        assert response.message == "success"
        assert response.data is None

    def test_custom_values(self):
        """测试自定义值"""
        response = ResponseModel(
            code=201,
            message="Created successfully",
            data={"id": 1, "name": "test"}
        )

        assert response.code == 201
        assert response.message == "Created successfully"
        assert response.data == {"id": 1, "name": "test"}

    def test_with_string_data(self):
        """测试字符串数据"""
        response = ResponseModel(data="Hello World")

        assert response.data == "Hello World"

    def test_with_list_data(self):
        """测试列表数据"""
        response = ResponseModel(data=[1, 2, 3])

        assert response.data == [1, 2, 3]

    def test_with_nested_dict(self):
        """测试嵌套字典数据"""
        nested_data = {
            "user": {"id": 1, "name": "test"},
            "settings": {"theme": "dark"}
        }
        response = ResponseModel(data=nested_data)

        assert response.data["user"]["id"] == 1
        assert response.data["settings"]["theme"] == "dark"


class TestPaginationParams:
    """分页参数模型测试"""

    def test_default_values(self):
        """测试默认值"""
        params = PaginationParams()

        assert params.page == 1
        assert params.page_size == 20

    def test_custom_values(self):
        """测试自定义值"""
        params = PaginationParams(page=2, page_size=50)

        assert params.page == 2
        assert params.page_size == 50

    def test_page_minimum_validation(self):
        """测试页码最小值验证"""
        with pytest.raises(ValidationError) as exc_info:
            PaginationParams(page=0)

        assert "page" in str(exc_info.value)

    def test_page_size_minimum_validation(self):
        """测试页大小最小值验证"""
        with pytest.raises(ValidationError) as exc_info:
            PaginationParams(page_size=0)

        assert "page_size" in str(exc_info.value)

    def test_page_size_maximum_validation(self):
        """测试页大小最大值验证"""
        with pytest.raises(ValidationError) as exc_info:
            PaginationParams(page_size=101)

        assert "page_size" in str(exc_info.value)

    def test_valid_boundary_values(self):
        """测试有效边界值"""
        # 最小值
        params1 = PaginationParams(page=1, page_size=1)
        assert params1.page == 1
        assert params1.page_size == 1

        # 最大值
        params2 = PaginationParams(page=1000, page_size=100)
        assert params2.page == 1000
        assert params2.page_size == 100


class TestPaginatedResponse:
    """分页响应模型测试"""

    def test_default_values(self):
        """测试默认值"""
        response = PaginatedResponse()

        assert response.items == []
        assert response.total == 0
        assert response.page == 1
        assert response.page_size == 20
        assert response.total_pages == 0

    def test_custom_values(self):
        """测试自定义值"""
        response = PaginatedResponse(
            items=[{"id": 1}, {"id": 2}],
            total=100,
            page=2,
            page_size=50
        )

        assert len(response.items) == 2
        assert response.total == 100
        assert response.page == 2
        assert response.page_size == 50

    def test_create_method(self):
        """测试create工厂方法"""
        items = [{"id": i} for i in range(1, 11)]
        response = PaginatedResponse.create(
            items=items,
            total=95,
            page=1,
            page_size=10
        )

        assert len(response.items) == 10
        assert response.total == 95
        assert response.page == 1
        assert response.page_size == 10
        assert response.total_pages == 10  # 95 / 10 = 9.5, 向上取整为10

    def test_total_pages_calculation(self):
        """测试总页数计算"""
        # 整除情况
        response1 = PaginatedResponse.create(
            items=[], total=100, page=1, page_size=10
        )
        assert response1.total_pages == 10

        # 有余数情况
        response2 = PaginatedResponse.create(
            items=[], total=95, page=1, page_size=10
        )
        assert response2.total_pages == 10

        # 边界情况：total=0
        response3 = PaginatedResponse.create(
            items=[], total=0, page=1, page_size=10
        )
        assert response3.total_pages == 0

    def test_create_with_empty_items(self):
        """测试创建空列表响应"""
        response = PaginatedResponse.create(
            items=[],
            total=0,
            page=1,
            page_size=20
        )

        assert response.items == []
        assert response.total == 0
        assert response.total_pages == 0

    def test_generic_type(self):
        """测试泛型类型"""
        # 字符串列表
        str_response = PaginatedResponse[str](
            items=["a", "b", "c"],
            total=3,
            page=1,
            page_size=10
        )
        assert all(isinstance(item, str) for item in str_response.items)

        # 整数列表
        int_response = PaginatedResponse[int](
            items=[1, 2, 3],
            total=3,
            page=1,
            page_size=10
        )
        assert all(isinstance(item, int) for item in int_response.items)


class TestErrorResponse:
    """错误响应模型测试"""

    def test_default_values(self):
        """测试默认值"""
        response = ErrorResponse()

        assert response.code == 500
        assert response.message == "Internal server error"
        assert response.detail is None

    def test_custom_values(self):
        """测试自定义值"""
        response = ErrorResponse(
            code=404,
            message="Not found",
            detail={"resource": "user", "id": 123}
        )

        assert response.code == 404
        assert response.message == "Not found"
        assert response.detail == {"resource": "user", "id": 123}

    def test_with_string_detail(self):
        """测试字符串详情"""
        response = ErrorResponse(
            code=400,
            message="Bad request",
            detail="Invalid parameter: name"
        )

        assert response.detail == "Invalid parameter: name"

    def test_with_list_detail(self):
        """测试列表详情"""
        response = ErrorResponse(
            code=422,
            message="Validation error",
            detail=["field1 is required", "field2 must be integer"]
        )

        assert isinstance(response.detail, list)
        assert len(response.detail) == 2

    def test_common_error_codes(self):
        """测试常见错误码"""
        error_codes = [
            (400, "Bad Request"),
            (401, "Unauthorized"),
            (403, "Forbidden"),
            (404, "Not Found"),
            (422, "Unprocessable Entity"),
            (429, "Too Many Requests"),
            (500, "Internal Server Error"),
            (502, "Bad Gateway"),
            (503, "Service Unavailable"),
        ]

        for code, message in error_codes:
            response = ErrorResponse(code=code, message=message)
            assert response.code == code
            assert response.message == message


class TestModelSerialization:
    """模型序列化测试"""

    def test_response_model_json(self):
        """测试响应模型JSON序列化"""
        response = ResponseModel(
            code=200,
            message="Success",
            data={"key": "value"}
        )

        json_data = response.model_dump()

        assert json_data["code"] == 200
        assert json_data["message"] == "Success"
        assert json_data["data"] == {"key": "value"}

    def test_paginated_response_json(self):
        """测试分页响应JSON序列化"""
        response = PaginatedResponse.create(
            items=[{"id": 1}, {"id": 2}],
            total=2,
            page=1,
            page_size=10
        )

        json_data = response.model_dump()

        assert "items" in json_data
        assert "total" in json_data
        assert "total_pages" in json_data
        assert json_data["total_pages"] == 1

    def test_error_response_json(self):
        """测试错误响应JSON序列化"""
        response = ErrorResponse(
            code=400,
            message="Validation failed",
            detail={"field": "email", "error": "Invalid format"}
        )

        json_data = response.model_dump()

        assert json_data["code"] == 400
        assert json_data["message"] == "Validation failed"
        assert json_data["detail"]["field"] == "email"
