from abc import ABC, abstractmethod
from typing import List, Optional

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        pass

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        pass


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model: str, api_key: str, base_url: str = ""):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url or "https://api.openai.com/v1"
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    )
    async def embed(self, text: str) -> list[float]:
        response = await self.client.post(
            "/embeddings",
            json={"model": self.model, "input": text},
        )
        response.raise_for_status()
        data = response.json()
        return data["data"][0]["embedding"]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        response = await self.client.post(
            "/embeddings",
            json={"model": self.model, "input": texts},
        )
        response.raise_for_status()
        data = response.json()
        return [item["embedding"] for item in data["data"]]

    async def close(self):
        await self.client.aclose()


class AnthropicEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model: str, api_key: str, base_url: str = ""):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url or "https://api.anthropic.com/v1"
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
            timeout=30.0,
        )

    async def embed(self, text: str) -> list[float]:
        logger.warning("anthropic_embeddings_not_supported", model=self.model)
        return [0.0] * 1536

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 1536 for _ in texts]

    async def close(self):
        await self.client.aclose()


class MockEmbeddingProvider(EmbeddingProvider):
    def __init__(self, dimension: int = 1536):
        self.dimension = dimension

    async def embed(self, text: str) -> list[float]:
        import hashlib

        hash_val = int(hashlib.sha256(text.encode()).hexdigest(), 16)
        return [(hash_val >> i & 1) * 0.01 for i in range(self.dimension)]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed(text) for text in texts]


class EmbeddingProviderFactory:
    @staticmethod
    def create_provider(
        provider: str, model: str, api_key: str, base_url: str = ""
    ) -> EmbeddingProvider:
        if provider == "openai":
            return OpenAIEmbeddingProvider(model, api_key, base_url)
        if provider == "anthropic":
            return AnthropicEmbeddingProvider(model, api_key, base_url)
        if provider == "mock" or settings.EVAL_MODE == "local":
            return MockEmbeddingProvider()
        logger.warning("unknown_embedding_provider", provider=provider)
        return MockEmbeddingProvider()


__all__ = [
    "AnthropicEmbeddingProvider",
    "EmbeddingProvider",
    "EmbeddingProviderFactory",
    "MockEmbeddingProvider",
    "OpenAIEmbeddingProvider",
]
