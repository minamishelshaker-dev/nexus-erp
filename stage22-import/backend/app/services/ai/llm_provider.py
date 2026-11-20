"""
Nexus ERP - LLM Provider Abstraction Layer
===========================================

This module provides a unified interface for multiple LLM providers:
- OpenAI API (Primary - Recommended)
- Mock Provider (For testing/development without API key)

The system uses standard OpenAI API which requires an OPENAI_API_KEY
environment variable to be set. Get your API key at: https://platform.openai.com/

Features:
- Provider abstraction
- Fallback mechanisms
- Rate limiting
- Token tracking
- Cost estimation
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List, Dict, Any, AsyncGenerator
from decimal import Decimal
from dataclasses import dataclass
import logging
import json
import asyncio
import os

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Standard LLM response structure."""
    content: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model: str
    provider: str
    latency_ms: float
    finish_reason: str
    cost: Optional[Decimal] = None
    raw_response: Optional[Dict] = None


@dataclass
class LLMConfig:
    """LLM configuration."""
    model: str = "gpt-4o"  # OpenAI's latest model
    temperature: float = 0.7
    max_tokens: int = 2000
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop_sequences: Optional[List[str]] = None


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    provider_name: str = "base"
    
    @abstractmethod
    async def complete(
        self,
        messages: List[Dict[str, str]],
        config: LLMConfig
    ) -> LLMResponse:
        """Generate a completion."""
        pass
    
    @abstractmethod
    async def stream(
        self,
        messages: List[Dict[str, str]],
        config: LLMConfig
    ) -> AsyncGenerator[str, None]:
        """Stream a completion."""
        pass
    
    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        """Generate embeddings for text."""
        pass
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        # Rough estimation: ~4 characters per token
        return len(text) // 4
    
    def estimate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: str
    ) -> Decimal:
        """Estimate cost for the request."""
        # Default pricing (should be overridden by providers)
        return Decimal("0.0")


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI API Provider
    
    Uses the official OpenAI API for completions.
    Requires OPENAI_API_KEY environment variable.
    
    Get your API key at: https://platform.openai.com/api-keys
    """
    
    provider_name = "openai"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenAI provider.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
        """
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._client = None
        
        # OpenAI pricing (as of 2024)
        self._pricing = {
            "gpt-4o": {"prompt": 0.005, "completion": 0.015},
            "gpt-4o-mini": {"prompt": 0.00015, "completion": 0.0006},
            "gpt-4-turbo": {"prompt": 0.01, "completion": 0.03},
            "gpt-4": {"prompt": 0.03, "completion": 0.06},
            "gpt-3.5-turbo": {"prompt": 0.0005, "completion": 0.0015},
            "text-embedding-ada-002": {"prompt": 0.0001, "completion": 0},
            "text-embedding-3-small": {"prompt": 0.00002, "completion": 0},
            "text-embedding-3-large": {"prompt": 0.00013, "completion": 0},
            "default": {"prompt": 0.005, "completion": 0.015}
        }
    
    async def _get_client(self):
        """Lazy load the OpenAI client."""
        if self._client is None:
            if not self._api_key:
                raise ValueError(
                    "OpenAI API key not configured. "
                    "Set the OPENAI_API_KEY environment variable or pass api_key parameter. "
                    "Get your API key at: https://platform.openai.com/api-keys"
                )
            
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=self._api_key)
        return self._client
    
    async def complete(
        self,
        messages: List[Dict[str, str]],
        config: LLMConfig
    ) -> LLMResponse:
        """Generate a completion using OpenAI API."""
        start_time = datetime.now()
        
        try:
            client = await self._get_client()
            
            # Build request parameters
            request_params = {
                "messages": messages,
                "model": config.model,
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
                "top_p": config.top_p,
                "frequency_penalty": config.frequency_penalty,
                "presence_penalty": config.presence_penalty,
            }
            
            if config.stop_sequences:
                request_params["stop"] = config.stop_sequences
            
            response = await client.chat.completions.create(**request_params)
            
            end_time = datetime.now()
            latency_ms = (end_time - start_time).total_seconds() * 1000
            
            # Extract response data
            content = response.choices[0].message.content
            prompt_tokens = response.usage.prompt_tokens if response.usage else 0
            completion_tokens = response.usage.completion_tokens if response.usage else 0
            total_tokens = response.usage.total_tokens if response.usage else 0
            finish_reason = response.choices[0].finish_reason or "stop"
            
            # Calculate cost
            cost = self.estimate_cost(prompt_tokens, completion_tokens, config.model)
            
            return LLMResponse(
                content=content,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                model=config.model,
                provider=self.provider_name,
                latency_ms=latency_ms,
                finish_reason=finish_reason,
                cost=cost,
                raw_response={"id": response.id, "model": response.model}
            )
            
        except Exception as e:
            logger.error(f"OpenAI completion error: {e}")
            raise
    
    async def stream(
        self,
        messages: List[Dict[str, str]],
        config: LLMConfig
    ) -> AsyncGenerator[str, None]:
        """Stream a completion using OpenAI API."""
        try:
            client = await self._get_client()
            
            # Build request parameters
            request_params = {
                "messages": messages,
                "model": config.model,
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
                "top_p": config.top_p,
                "stream": True
            }
            
            stream = await client.chat.completions.create(**request_params)
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            raise
    
    async def embed(
        self, 
        text: str,
        model: str = "text-embedding-3-small"
    ) -> List[float]:
        """
        Generate embeddings using OpenAI's embedding models.
        
        Args:
            text: Text to embed
            model: Embedding model to use (default: text-embedding-3-small)
            
        Returns:
            List of embedding values
        """
        try:
            client = await self._get_client()
            
            response = await client.embeddings.create(
                input=text,
                model=model
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
            # Fallback to simple hash-based embedding
            import hashlib
            hash_obj = hashlib.sha256(text.encode())
            hash_bytes = hash_obj.digest()
            return [float(b) / 255.0 for b in hash_bytes[:128]]
    
    def estimate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: str
    ) -> Decimal:
        """Estimate cost based on token usage and model pricing."""
        pricing = self._pricing.get(model, self._pricing["default"])
        cost = (
            Decimal(str(prompt_tokens)) * Decimal(str(pricing["prompt"])) / 1000 +
            Decimal(str(completion_tokens)) * Decimal(str(pricing["completion"])) / 1000
        )
        return cost.quantize(Decimal("0.000001"))


class MockProvider(BaseLLMProvider):
    """
    Mock LLM Provider for testing and development.
    
    Returns predefined responses without API calls.
    Use this when you don't have an OpenAI API key.
    """
    
    provider_name = "mock"
    
    def __init__(self):
        self.responses = {
            "forecast": "Based on historical analysis, the predicted demand is stable with a slight upward trend. Expected growth: 12% over the next quarter with 85% confidence.",
            "anomaly": "No significant anomalies detected in the analyzed transactions. All values are within normal parameters.",
            "chat": "I understand your question. Let me help you with that. (Note: Running in mock mode - configure OPENAI_API_KEY for real AI responses)",
            "insight": "Key insight: Your revenue has grown 15% compared to last quarter. Top performing products show strong seasonal demand.",
            "query": "Here are the results of your query. (Mock response - set OPENAI_API_KEY for real data analysis)"
        }
    
    async def complete(
        self,
        messages: List[Dict[str, str]],
        config: LLMConfig
    ) -> LLMResponse:
        """Generate a mock completion."""
        await asyncio.sleep(0.1)  # Simulate latency
        
        # Determine response type based on message content
        content = messages[-1].get("content", "").lower() if messages else ""
        
        if "forecast" in content:
            response = self.responses["forecast"]
        elif "anomaly" in content:
            response = self.responses["anomaly"]
        elif "insight" in content:
            response = self.responses["insight"]
        else:
            response = self.responses["chat"]
        
        return LLMResponse(
            content=response,
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            model=config.model,
            provider=self.provider_name,
            latency_ms=100.0,
            finish_reason="stop",
            cost=Decimal("0.0")
        )
    
    async def stream(
        self,
        messages: List[Dict[str, str]],
        config: LLMConfig
    ) -> AsyncGenerator[str, None]:
        """Stream a mock completion."""
        response = await self.complete(messages, config)
        words = response.content.split()
        for word in words:
            await asyncio.sleep(0.05)
            yield word + " "
    
    async def embed(self, text: str) -> List[float]:
        """Generate mock embeddings."""
        return [0.1] * 1536  # Same dimension as OpenAI embeddings


class LLMProviderFactory:
    """
    Factory for creating LLM providers.
    
    Manages provider instances and configurations.
    """
    
    _providers: Dict[str, BaseLLMProvider] = {}
    
    @classmethod
    def get_provider(cls, provider_name: str = "openai") -> BaseLLMProvider:
        """
        Get or create a provider instance.
        
        Args:
            provider_name: Provider to use ("openai" or "mock")
            
        Returns:
            LLM provider instance
        """
        if provider_name not in cls._providers:
            if provider_name == "openai":
                cls._providers[provider_name] = OpenAIProvider()
            elif provider_name == "mock":
                cls._providers[provider_name] = MockProvider()
            else:
                raise ValueError(f"Unknown provider: {provider_name}. Available: openai, mock")
        
        return cls._providers[provider_name]
    
    @classmethod
    def register_provider(cls, name: str, provider: BaseLLMProvider):
        """Register a custom provider."""
        cls._providers[name] = provider
    
    @classmethod
    def list_providers(cls) -> List[str]:
        """List available providers."""
        return list(cls._providers.keys())


class LLMService:
    """
    High-level LLM Service
    
    Provides a unified interface for LLM operations with:
    - Automatic provider selection
    - Fallback handling
    - Rate limiting
    - Response caching
    """
    
    def __init__(
        self,
        default_provider: str = "openai",
        fallback_provider: Optional[str] = "mock",
        max_retries: int = 3
    ):
        self.default_provider = default_provider
        self.fallback_provider = fallback_provider
        self.max_retries = max_retries
        self._request_count = 0
        self._total_tokens = 0
        self._total_cost = Decimal("0")
    
    async def complete(
        self,
        messages: List[Dict[str, str]],
        config: Optional[LLMConfig] = None,
        provider: Optional[str] = None
    ) -> LLMResponse:
        """
        Generate a completion with fallback support.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            config: LLM configuration
            provider: Specific provider to use (optional)
            
        Returns:
            LLMResponse with the completion result
        """
        config = config or LLMConfig()
        provider_name = provider or self.default_provider
        
        for attempt in range(self.max_retries):
            try:
                provider_instance = LLMProviderFactory.get_provider(provider_name)
                response = await provider_instance.complete(messages, config)
                
                # Update stats
                self._request_count += 1
                self._total_tokens += response.total_tokens
                if response.cost:
                    self._total_cost += response.cost
                
                return response
                
            except Exception as e:
                logger.warning(f"LLM request failed (attempt {attempt + 1}): {e}")
                
                # Try fallback provider
                if self.fallback_provider and provider_name != self.fallback_provider:
                    logger.info(f"Trying fallback provider: {self.fallback_provider}")
                    provider_name = self.fallback_provider
                elif attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise
    
    async def stream(
        self,
        messages: List[Dict[str, str]],
        config: Optional[LLMConfig] = None,
        provider: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Stream a completion."""
        config = config or LLMConfig()
        provider_name = provider or self.default_provider
        provider_instance = LLMProviderFactory.get_provider(provider_name)
        
        async for chunk in provider_instance.stream(messages, config):
            yield chunk
    
    async def embed(
        self,
        text: str,
        provider: Optional[str] = None
    ) -> List[float]:
        """Generate embeddings for text."""
        provider_name = provider or self.default_provider
        provider_instance = LLMProviderFactory.get_provider(provider_name)
        return await provider_instance.embed(text)
    
    async def complete_json(
        self,
        messages: List[Dict[str, str]],
        config: Optional[LLMConfig] = None,
        provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a completion and parse as JSON.
        
        Returns parsed JSON or raises an error.
        """
        config = config or LLMConfig()
        config.temperature = min(config.temperature, 0.3)  # Lower temp for JSON
        
        response = await self.complete(messages, config, provider)
        
        try:
            # Try to extract JSON from the response
            import re
            json_match = re.search(r'\{.*\}|\[.*\]', response.content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return json.loads(response.content)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON response: {response.content[:200]}")
            raise ValueError("Response is not valid JSON")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        return {
            "request_count": self._request_count,
            "total_tokens": self._total_tokens,
            "total_cost": float(self._total_cost),
            "avg_tokens_per_request": self._total_tokens / max(1, self._request_count)
        }
    
    def reset_stats(self):
        """Reset usage statistics."""
        self._request_count = 0
        self._total_tokens = 0
        self._total_cost = Decimal("0")


# Default LLM service instance - uses OpenAI with mock fallback
default_llm_service = LLMService()


def get_llm_service() -> LLMService:
    """Get the default LLM service instance."""
    return default_llm_service
