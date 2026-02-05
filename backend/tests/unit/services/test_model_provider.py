"""
模型提供商服务单元测试
"""
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.model_provider import (
    AzureModelFetcher,
    BaseModelFetcher,
    CohereModelFetcher,
    FETCHER_REGISTRY,
    GeminiModelFetcher,
    MistralModelFetcher,
    OpenAIModelFetcher,
    ProviderModel,
    get_model_fetcher,
)


class TestProviderModel:
    """提供商模型测试"""

    def test_provider_model_creation(self):
        """测试模型创建"""
        model = ProviderModel(
            id="gpt-4",
            name="GPT-4",
            provider="OpenAI",
            channel_type="openai"
        )

        assert model.id == "gpt-4"
        assert model.name == "GPT-4"
        assert model.provider == "OpenAI"
        assert model.channel_type == "openai"

    def test_default_capabilities(self):
        """测试默认能力"""
        model = ProviderModel(
            id="test-model",
            name="Test Model",
            provider="Test",
            channel_type="test"
        )

        assert "chat" in model.capabilities

    def test_custom_capabilities(self):
        """测试自定义能力"""
        model = ProviderModel(
            id="gpt-4-vision",
            name="GPT-4 Vision",
            provider="OpenAI",
            channel_type="openai",
            capabilities=["chat", "vision", "function_calling"]
        )

        assert "chat" in model.capabilities
        assert "vision" in model.capabilities
        assert "function_calling" in model.capabilities

    def test_optional_fields(self):
        """测试可选字段"""
        model = ProviderModel(
            id="test-model",
            name="Test",
            provider="Test",
            channel_type="test",
            context_window=4096,
            description="A test model"
        )

        assert model.context_window == 4096
        assert model.description == "A test model"


class TestBaseModelFetcher:
    """基础模型获取器测试"""

    def test_detect_capabilities_chat(self):
        """测试聊天能力检测"""
        fetcher = BaseModelFetcher()

        # 基本聊天模型
        caps = fetcher._detect_capabilities("gpt-3.5-turbo")
        assert "chat" in caps

    def test_detect_capabilities_vision(self):
        """测试视觉能力检测"""
        fetcher = BaseModelFetcher()

        # GPT-4
        caps = fetcher._detect_capabilities("gpt-4")
        assert "vision" in caps

        # Claude-3
        caps = fetcher._detect_capabilities("claude-3-opus")
        assert "vision" in caps

        # Gemini
        caps = fetcher._detect_capabilities("gemini-pro")
        assert "vision" in caps

    def test_detect_capabilities_function_calling(self):
        """测试函数调用能力检测"""
        fetcher = BaseModelFetcher()

        # GPT-4
        caps = fetcher._detect_capabilities("gpt-4")
        assert "function_calling" in caps

        # GPT-3.5
        caps = fetcher._detect_capabilities("gpt-3.5-turbo")
        assert "function_calling" in caps

        # Claude-3
        caps = fetcher._detect_capabilities("claude-3-sonnet")
        assert "function_calling" in caps

    def test_estimate_context_window_openai(self):
        """测试OpenAI模型上下文窗口估计"""
        fetcher = BaseModelFetcher()

        assert fetcher._estimate_context_window("gpt-4-turbo") == 128000
        assert fetcher._estimate_context_window("gpt-4o") == 128000
        assert fetcher._estimate_context_window("gpt-4-32k") == 32768
        assert fetcher._estimate_context_window("gpt-4") == 8192
        assert fetcher._estimate_context_window("gpt-3.5-turbo-16k") == 16384
        assert fetcher._estimate_context_window("gpt-3.5-turbo") == 4096

    def test_estimate_context_window_anthropic(self):
        """测试Anthropic模型上下文窗口估计"""
        fetcher = BaseModelFetcher()

        assert fetcher._estimate_context_window("claude-3-opus") == 200000
        assert fetcher._estimate_context_window("claude-3-sonnet") == 200000
        assert fetcher._estimate_context_window("claude-2") == 100000

    def test_estimate_context_window_gemini(self):
        """测试Gemini模型上下文窗口估计"""
        fetcher = BaseModelFetcher()

        assert fetcher._estimate_context_window("gemini-1.5-pro") == 2000000
        assert fetcher._estimate_context_window("gemini-1.5-flash") == 1000000
        assert fetcher._estimate_context_window("gemini-pro") == 32768

    def test_estimate_context_window_unknown(self):
        """测试未知模型上下文窗口"""
        fetcher = BaseModelFetcher()

        assert fetcher._estimate_context_window("unknown-model") is None

    def test_fetch_models_not_implemented(self):
        """测试fetch_models未实现"""
        fetcher = BaseModelFetcher()

        with pytest.raises(NotImplementedError):
            # 需要使用async，但这里直接测试会抛出NotImplementedError
            import asyncio
            asyncio.run(fetcher.fetch_models("test-key"))


class TestOpenAIModelFetcher:
    """OpenAI模型获取器测试"""

    def test_is_chat_model(self):
        """测试聊天模型识别"""
        fetcher = OpenAIModelFetcher()

        # 聊天模型
        assert fetcher._is_chat_model("gpt-4") is True
        assert fetcher._is_chat_model("gpt-3.5-turbo") is True
        assert fetcher._is_chat_model("o1-preview") is True
        assert fetcher._is_chat_model("o3-mini") is True

        # 非聊天模型
        assert fetcher._is_chat_model("text-embedding-3-small") is False
        assert fetcher._is_chat_model("tts-1") is False
        assert fetcher._is_chat_model("whisper-1") is False
        assert fetcher._is_chat_model("dall-e-3") is False

    def test_format_name(self):
        """测试模型名称格式化"""
        fetcher = OpenAIModelFetcher()

        assert fetcher._format_name("gpt-4o") == "GPT-4o"
        assert fetcher._format_name("gpt-4o-mini") == "GPT-4o Mini"
        assert fetcher._format_name("gpt-4-turbo") == "GPT-4 Turbo"
        assert fetcher._format_name("gpt-3.5-turbo") == "GPT-3.5 Turbo"
        assert fetcher._format_name("o1-mini") == "O1 Mini"
        assert fetcher._format_name("custom-model") == "Custom Model"

    @pytest.mark.asyncio
    async def test_fetch_models_success(self):
        """测试成功获取模型列表"""
        fetcher = OpenAIModelFetcher()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"id": "gpt-4"},
                {"id": "gpt-3.5-turbo"},
                {"id": "text-embedding-ada-002"},  # 应该被过滤
            ]
        }

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.get.return_value = mock_response

        with patch('httpx.AsyncClient', return_value=mock_client):
            models = await fetcher.fetch_models("test-api-key")

            assert len(models) == 2  # embedding被过滤
            assert any(m.id == "gpt-4" for m in models)
            assert any(m.id == "gpt-3.5-turbo" for m in models)

    @pytest.mark.asyncio
    async def test_fetch_models_http_error(self):
        """测试HTTP错误处理"""
        fetcher = OpenAIModelFetcher()

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized",
            request=MagicMock(),
            response=MagicMock(status_code=401, text="Invalid API key")
        )

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.get.return_value = mock_response

        with patch('httpx.AsyncClient', return_value=mock_client):
            with pytest.raises(httpx.HTTPStatusError):
                await fetcher.fetch_models("invalid-key")


class TestAzureModelFetcher:
    """Azure模型获取器测试"""

    def test_is_chat_model(self):
        """测试Azure聊天模型识别"""
        fetcher = AzureModelFetcher()

        assert fetcher._is_chat_model("gpt-4") is True
        assert fetcher._is_chat_model("gpt-35-turbo") is True
        assert fetcher._is_chat_model("text-embedding-ada-002") is False

    def test_format_name(self):
        """测试Azure模型名称格式化"""
        fetcher = AzureModelFetcher()

        assert fetcher._format_name("gpt-4") == "Azure Gpt 4"
        assert fetcher._format_name("gpt-35-turbo") == "Azure Gpt 35 Turbo"

    @pytest.mark.asyncio
    async def test_fetch_models_without_api_base(self):
        """测试缺少api_base的错误"""
        fetcher = AzureModelFetcher()

        with pytest.raises(ValueError) as exc_info:
            await fetcher.fetch_models("test-key", api_base=None)

        assert "api_base" in str(exc_info.value).lower()


class TestAnthropicModelFetcher:
    """Anthropic模型获取器测试"""

    def test_format_name(self):
        """测试Anthropic模型名称格式化"""
        fetcher = AnthropicModelFetcher()

        assert fetcher._format_name("claude-3-opus-20240229") == "Claude 3 Opus"
        assert fetcher._format_name("claude-3-sonnet-20240229") == "Claude 3 Sonnet"
        assert fetcher._format_name("claude-3-haiku-20240307") == "Claude 3 Haiku"
        assert fetcher._format_name("claude-3-5-sonnet-20241022") == "Claude 3.5 Sonnet (New)"
        assert fetcher._format_name("custom-model") == "Custom Model"


class TestGeminiModelFetcher:
    """Gemini模型获取器测试"""

    def test_format_name(self):
        """测试Gemini模型名称格式化"""
        fetcher = GeminiModelFetcher()

        assert fetcher._format_name("gemini-1.5-pro") == "Gemini 1.5 Pro"
        assert fetcher._format_name("gemini-1.5-flash") == "Gemini 1.5 Flash"
        assert fetcher._format_name("gemini-1.0-pro") == "Gemini 1.0 Pro"
        assert fetcher._format_name("gemini-pro") == "Gemini Pro"


class TestMistralModelFetcher:
    """Mistral模型获取器测试"""

    def test_format_name(self):
        """测试Mistral模型名称格式化"""
        fetcher = MistralModelFetcher()

        assert fetcher._format_name("mistral-large-latest") == "Mistral Large"
        assert fetcher._format_name("mistral-medium-latest") == "Mistral Medium"
        assert fetcher._format_name("codestral-latest") == "Codestral"

    def test_estimate_context_window(self):
        """测试Mistral上下文窗口估计"""
        fetcher = MistralModelFetcher()

        assert fetcher._estimate_context_window("mistral-large-latest") == 128000
        assert fetcher._estimate_context_window("mistral-medium-latest") == 32000
        assert fetcher._estimate_context_window("mistral-small-latest") == 32000
        assert fetcher._estimate_context_window("unknown") == 32000


class TestCohereModelFetcher:
    """Cohere模型获取器测试"""

    def test_format_name(self):
        """测试Cohere模型名称格式化"""
        fetcher = CohereModelFetcher()

        assert fetcher._format_name("command-r") == "Command R"
        assert fetcher._format_name("command-r-plus") == "Command R+"
        assert fetcher._format_name("command-r7b") == "Command R7B"
        assert fetcher._format_name("c4ai-aya-expanse-8b") == "Aya Expanse 8B"


class TestFetcherRegistry:
    """获取器注册表测试"""

    def test_registry_contents(self):
        """测试注册表内容"""
        assert "openai" in FETCHER_REGISTRY
        assert "azure" in FETCHER_REGISTRY
        assert "anthropic" in FETCHER_REGISTRY
        assert "gemini" in FETCHER_REGISTRY
        assert "mistral" in FETCHER_REGISTRY
        assert "cohere" in FETCHER_REGISTRY

    def test_registry_fetcher_types(self):
        """测试注册表获取器类型"""
        assert FETCHER_REGISTRY["openai"] == OpenAIModelFetcher
        assert FETCHER_REGISTRY["azure"] == AzureModelFetcher
        assert FETCHER_REGISTRY["anthropic"] == AnthropicModelFetcher
        assert FETCHER_REGISTRY["gemini"] == GeminiModelFetcher


class TestGetModelFetcher:
    """get_model_fetcher函数测试"""

    def test_get_openai_fetcher(self):
        """测试获取OpenAI获取器"""
        fetcher = get_model_fetcher("openai")
        assert isinstance(fetcher, OpenAIModelFetcher)

    def test_get_azure_fetcher(self):
        """测试获取Azure获取器"""
        fetcher = get_model_fetcher("azure")
        assert isinstance(fetcher, AzureModelFetcher)

    def test_get_anthropic_fetcher(self):
        """测试获取Anthropic获取器"""
        fetcher = get_model_fetcher("anthropic")
        assert isinstance(fetcher, AnthropicModelFetcher)

    def test_get_gemini_fetcher(self):
        """测试获取Gemini获取器"""
        fetcher = get_model_fetcher("gemini")
        assert isinstance(fetcher, GeminiModelFetcher)

    def test_case_insensitive(self):
        """测试大小写不敏感"""
        fetcher1 = get_model_fetcher("OPENAI")
        fetcher2 = get_model_fetcher("OpenAI")
        fetcher3 = get_model_fetcher("openai")

        assert isinstance(fetcher1, OpenAIModelFetcher)
        assert isinstance(fetcher2, OpenAIModelFetcher)
        assert isinstance(fetcher3, OpenAIModelFetcher)

    def test_invalid_channel_type(self):
        """测试无效渠道类型"""
        fetcher = get_model_fetcher("invalid-type")
        assert fetcher is None

    def test_unknown_provider(self):
        """测试未知提供商"""
        fetcher = get_model_fetcher("unknown-provider")
        assert fetcher is None
