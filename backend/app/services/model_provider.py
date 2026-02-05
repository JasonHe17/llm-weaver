"""
模型提供商服务
从各个厂商API获取模型列表
"""

from typing import Dict, List, Optional, Any
import httpx
from dataclasses import dataclass

from app.core.logging import logger


@dataclass
class ProviderModel:
    """提供商模型信息."""
    
    id: str
    name: str
    provider: str
    channel_type: str
    context_window: Optional[int] = None
    capabilities: List[str] = None
    description: str = ""
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = ["chat"]


class BaseModelFetcher:
    """基础模型获取器."""
    
    provider_name: str = ""
    channel_type: str = ""
    
    async def fetch_models(
        self,
        api_key: str,
        api_base: Optional[str] = None,
        api_version: Optional[str] = None,
        **kwargs
    ) -> List[ProviderModel]:
        """获取模型列表.
        
        Args:
            api_key: API密钥
            api_base: API基础地址
            api_version: API版本
            
        Returns:
            模型列表
        """
        raise NotImplementedError
    
    def _detect_capabilities(self, model_id: str) -> List[str]:
        """根据模型ID检测能力.
        
        Args:
            model_id: 模型ID
            
        Returns:
            能力列表
        """
        capabilities = ["chat"]
        model_lower = model_id.lower()
        
        # Vision support
        if any(kw in model_lower for kw in ["vision", "gpt-4", "claude-3", "gemini"]):
            capabilities.append("vision")
        
        # Function calling support
        if any(kw in model_lower for kw in [
            "gpt-4", "gpt-3.5", "claude-3", "claude-3-5"
        ]):
            capabilities.append("function_calling")
        
        return capabilities
    
    def _estimate_context_window(self, model_id: str) -> Optional[int]:
        """估计上下文窗口大小.
        
        Args:
            model_id: 模型ID
            
        Returns:
            上下文窗口大小
        """
        model_lower = model_id.lower()
        
        # OpenAI models
        if "gpt-4-turbo" in model_lower or "gpt-4o" in model_lower:
            return 128000
        elif "gpt-4" in model_lower and "32k" in model_lower:
            return 32768
        elif "gpt-4" in model_lower:
            return 8192
        elif "gpt-3.5" in model_lower and "16k" in model_lower:
            return 16384
        elif "gpt-3.5" in model_lower:
            return 4096
        
        # Anthropic models
        elif "claude-3" in model_lower:
            return 200000
        elif "claude" in model_lower:
            return 100000
        
        # Gemini models
        elif "gemini-1.5-pro" in model_lower:
            return 2000000
        elif "gemini-1.5-flash" in model_lower:
            return 1000000
        elif "gemini" in model_lower:
            return 32768
        
        return None


class OpenAIModelFetcher(BaseModelFetcher):
    """OpenAI模型获取器."""
    
    provider_name = "OpenAI"
    channel_type = "openai"
    
    async def fetch_models(
        self,
        api_key: str,
        api_base: Optional[str] = None,
        api_version: Optional[str] = None,
        organization: Optional[str] = None,
    ) -> List[ProviderModel]:
        """从OpenAI API获取模型列表."""
        api_base = api_base or "https://api.openai.com"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
        }
        if organization:
            headers["OpenAI-Organization"] = organization
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{api_base}/v1/models",
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
                
                models = []
                for item in data.get("data", []):
                    model_id = item.get("id", "")
                    
                    # Skip non-chat models
                    if not self._is_chat_model(model_id):
                        continue
                    
                    models.append(ProviderModel(
                        id=model_id,
                        name=self._format_name(model_id),
                        provider=self.provider_name,
                        channel_type=self.channel_type,
                        context_window=self._estimate_context_window(model_id),
                        capabilities=self._detect_capabilities(model_id),
                    ))
                
                return models
                
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenAI API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Failed to fetch OpenAI models: {e}")
            raise
    
    def _is_chat_model(self, model_id: str) -> bool:
        """检查是否为聊天模型."""
        # Skip embeddings, audio, moderation models
        skip_prefixes = [
            "text-embedding", "embedding", "tts-", "whisper-", "davinci",
            "curie", "babbage", "ada", "dall-e", "omni-moderation"
        ]
        model_lower = model_id.lower()
        
        for prefix in skip_prefixes:
            if model_lower.startswith(prefix) or prefix in model_lower:
                return False
        
        # Include chat/completion models
        chat_patterns = [
            "gpt-", "chatgpt-", "o1-", "o3-"
        ]
        
        for pattern in chat_patterns:
            if pattern in model_lower:
                return True
        
        return False
    
    def _format_name(self, model_id: str) -> str:
        """格式化模型名称."""
        name_map = {
            "gpt-4o": "GPT-4o",
            "gpt-4o-mini": "GPT-4o Mini",
            "gpt-4-turbo": "GPT-4 Turbo",
            "gpt-4": "GPT-4",
            "gpt-3.5-turbo": "GPT-3.5 Turbo",
            "chatgpt-4o-latest": "ChatGPT-4o Latest",
            "o1": "O1",
            "o1-mini": "O1 Mini",
            "o1-preview": "O1 Preview",
        }
        
        return name_map.get(model_id, model_id.replace("-", " ").title())


class AzureModelFetcher(BaseModelFetcher):
    """Azure OpenAI模型获取器."""
    
    provider_name = "Azure"
    channel_type = "azure"
    
    async def fetch_models(
        self,
        api_key: str,
        api_base: str,
        api_version: str = "2024-02-01",
        **kwargs
    ) -> List[ProviderModel]:
        """从Azure OpenAI API获取模型列表."""
        if not api_base:
            raise ValueError("Azure requires api_base")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{api_base}/openai/models?api-version={api_version}",
                    headers={"api-key": api_key},
                )
                response.raise_for_status()
                data = response.json()
                
                models = []
                for item in data.get("data", []):
                    model_id = item.get("id", "")
                    
                    # Skip non-chat models
                    if not self._is_chat_model(model_id):
                        continue
                    
                    models.append(ProviderModel(
                        id=model_id,
                        name=self._format_name(model_id),
                        provider=self.provider_name,
                        channel_type=self.channel_type,
                        context_window=self._estimate_context_window(model_id),
                        capabilities=self._detect_capabilities(model_id),
                    ))
                
                return models
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Azure API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Failed to fetch Azure models: {e}")
            raise
    
    def _is_chat_model(self, model_id: str) -> bool:
        """检查是否为聊天模型."""
        skip_prefixes = ["text-embedding", "embedding"]
        model_lower = model_id.lower()
        
        for prefix in skip_prefixes:
            if prefix in model_lower:
                return False
        
        return "gpt-" in model_lower or "chat" in model_lower
    
    def _format_name(self, model_id: str) -> str:
        """格式化模型名称."""
        return f"Azure {model_id.replace('-', ' ').title()}"


class AnthropicModelFetcher(BaseModelFetcher):
    """Anthropic模型获取器."""
    
    provider_name = "Anthropic"
    channel_type = "anthropic"
    
    async def fetch_models(
        self,
        api_key: str,
        api_base: Optional[str] = None,
        api_version: str = "2023-06-01",
        **kwargs
    ) -> List[ProviderModel]:
        """从Anthropic API获取模型列表."""
        api_base = api_base or "https://api.anthropic.com"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{api_base}/v1/models",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": api_version,
                    },
                )
                response.raise_for_status()
                data = response.json()
                
                models = []
                for item in data.get("data", []):
                    model_id = item.get("id", "")
                    
                    models.append(ProviderModel(
                        id=model_id,
                        name=self._format_name(model_id),
                        provider=self.provider_name,
                        channel_type=self.channel_type,
                        context_window=self._estimate_context_window(model_id),
                        capabilities=self._detect_capabilities(model_id),
                    ))
                
                return models
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Anthropic API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Failed to fetch Anthropic models: {e}")
            raise
    
    def _format_name(self, model_id: str) -> str:
        """格式化模型名称."""
        name_map = {
            "claude-3-opus-20240229": "Claude 3 Opus",
            "claude-3-sonnet-20240229": "Claude 3 Sonnet",
            "claude-3-haiku-20240307": "Claude 3 Haiku",
            "claude-3-5-sonnet-20240620": "Claude 3.5 Sonnet",
            "claude-3-5-sonnet-20241022": "Claude 3.5 Sonnet (New)",
            "claude-3-5-haiku-20241022": "Claude 3.5 Haiku",
        }
        
        return name_map.get(model_id, model_id.replace("-", " ").title())


class GeminiModelFetcher(BaseModelFetcher):
    """Google Gemini模型获取器."""
    
    provider_name = "Google"
    channel_type = "gemini"
    
    async def fetch_models(
        self,
        api_key: str,
        api_base: Optional[str] = None,
        api_version: str = "v1beta",
        **kwargs
    ) -> List[ProviderModel]:
        """从Google Gemini API获取模型列表."""
        api_base = api_base or "https://generativelanguage.googleapis.com"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{api_base}/{api_version}/models?key={api_key}",
                )
                response.raise_for_status()
                data = response.json()
                
                models = []
                for item in data.get("models", []):
                    model_id = item.get("name", "").replace("models/", "")
                    
                    # Skip embedding and other non-chat models
                    if "embedding" in model_lower or "aqa" in model_lower:
                        continue
                    
                    model_lower = model_id.lower()
                    
                    models.append(ProviderModel(
                        id=model_id,
                        name=self._format_name(model_id),
                        provider=self.provider_name,
                        channel_type=self.channel_type,
                        context_window=self._estimate_context_window(model_id),
                        capabilities=self._detect_capabilities(model_id),
                    ))
                
                return models
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Gemini API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Failed to fetch Gemini models: {e}")
            raise
    
    def _format_name(self, model_id: str) -> str:
        """格式化模型名称."""
        name_map = {
            "gemini-1.5-pro": "Gemini 1.5 Pro",
            "gemini-1.5-flash": "Gemini 1.5 Flash",
            "gemini-1.5-pro-latest": "Gemini 1.5 Pro Latest",
            "gemini-1.5-flash-latest": "Gemini 1.5 Flash Latest",
            "gemini-1.0-pro": "Gemini 1.0 Pro",
            "gemini-1.0-pro-vision": "Gemini 1.0 Pro Vision",
            "gemini-pro": "Gemini Pro",
            "gemini-pro-vision": "Gemini Pro Vision",
        }
        
        return name_map.get(model_id, model_id.replace("-", " ").title())


class MistralModelFetcher(BaseModelFetcher):
    """Mistral模型获取器."""
    
    provider_name = "Mistral"
    channel_type = "mistral"
    
    async def fetch_models(
        self,
        api_key: str,
        api_base: Optional[str] = None,
        **kwargs
    ) -> List[ProviderModel]:
        """从Mistral API获取模型列表."""
        api_base = api_base or "https://api.mistral.ai"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{api_base}/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                response.raise_for_status()
                data = response.json()
                
                models = []
                for item in data.get("data", []):
                    model_id = item.get("id", "")
                    
                    models.append(ProviderModel(
                        id=model_id,
                        name=self._format_name(model_id),
                        provider=self.provider_name,
                        channel_type=self.channel_type,
                        context_window=self._estimate_context_window(model_id),
                        capabilities=self._detect_capabilities(model_id),
                    ))
                
                return models
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Mistral API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Failed to fetch Mistral models: {e}")
            raise
    
    def _format_name(self, model_id: str) -> str:
        """格式化模型名称."""
        name_map = {
            "mistral-large-latest": "Mistral Large",
            "mistral-medium-latest": "Mistral Medium",
            "mistral-small-latest": "Mistral Small",
            "codestral-latest": "Codestral",
            "pixtral-large-latest": "Pixtral Large",
            "ministral-3b-latest": "Ministral 3B",
            "ministral-8b-latest": "Ministral 8B",
        }
        
        return name_map.get(model_id, model_id.replace("-", " ").title())
    
    def _estimate_context_window(self, model_id: str) -> Optional[int]:
        """估计上下文窗口大小."""
        model_lower = model_id.lower()
        
        if "large" in model_lower:
            return 128000
        elif "medium" in model_lower:
            return 32000
        elif "small" in model_lower:
            return 32000
        
        return 32000


class CohereModelFetcher(BaseModelFetcher):
    """Cohere模型获取器."""
    
    provider_name = "Cohere"
    channel_type = "cohere"
    
    async def fetch_models(
        self,
        api_key: str,
        api_base: Optional[str] = None,
        **kwargs
    ) -> List[ProviderModel]:
        """从Cohere API获取模型列表."""
        api_base = api_base or "https://api.cohere.com"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{api_base}/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                response.raise_for_status()
                data = response.json()
                
                models = []
                for item in data.get("models", []):
                    model_id = item.get("name", "")
                    
                    # Only include chat/command models
                    if not any(kw in model_id.lower() for kw in ["command", "c4ai"]):
                        continue
                    
                    models.append(ProviderModel(
                        id=model_id,
                        name=self._format_name(model_id),
                        provider=self.provider_name,
                        channel_type=self.channel_type,
                        context_window=item.get("context_length", 128000),
                        capabilities=self._detect_capabilities(model_id),
                    ))
                
                return models
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Cohere API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Failed to fetch Cohere models: {e}")
            raise
    
    def _format_name(self, model_id: str) -> str:
        """格式化模型名称."""
        name_map = {
            "command-r": "Command R",
            "command-r-plus": "Command R+",
            "command-r7b": "Command R7B",
            "command": "Command",
            "command-light": "Command Light",
            "command-nightly": "Command Nightly",
            "c4ai-aya-expanse-8b": "Aya Expanse 8B",
            "c4ai-aya-expanse-32b": "Aya Expanse 32B",
        }
        
        return name_map.get(model_id, model_id.replace("-", " ").title())


# Provider fetcher registry
FETCHER_REGISTRY: Dict[str, type[BaseModelFetcher]] = {
    "openai": OpenAIModelFetcher,
    "azure": AzureModelFetcher,
    "anthropic": AnthropicModelFetcher,
    "gemini": GeminiModelFetcher,
    "mistral": MistralModelFetcher,
    "cohere": CohereModelFetcher,
}


def get_model_fetcher(channel_type: str) -> Optional[BaseModelFetcher]:
    """获取对应类型的模型获取器.
    
    Args:
        channel_type: 渠道类型
        
    Returns:
        模型获取器实例或None
    """
    fetcher_class = FETCHER_REGISTRY.get(channel_type.lower())
    if fetcher_class:
        return fetcher_class()
    return None


async def fetch_models_from_channel(
    channel_type: str,
    api_key: str,
    api_base: Optional[str] = None,
    api_version: Optional[str] = None,
    **kwargs
) -> List[ProviderModel]:
    """从指定渠道获取模型列表.
    
    Args:
        channel_type: 渠道类型
        api_key: API密钥
        api_base: API基础地址
        api_version: API版本
        
    Returns:
        模型列表
        
    Raises:
        ValueError: 不支持的渠道类型
        Exception: API调用失败
    """
    fetcher = get_model_fetcher(channel_type)
    if not fetcher:
        raise ValueError(f"不支持的渠道类型: {channel_type}")
    
    return await fetcher.fetch_models(
        api_key=api_key,
        api_base=api_base,
        api_version=api_version,
        **kwargs
    )
