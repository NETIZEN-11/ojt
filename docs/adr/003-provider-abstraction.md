# ADR 003: Provider Abstraction Pattern

## Status
Accepted

## Context
The framework integrates with multiple external services:
- LLM providers (OpenAI, Anthropic, Google, local models)
- Embedding providers (OpenAI, Cohere, local)
- Target agents (HTTP APIs, custom protocols)
- Object storage (S3, MinIO, GCS, Azure Blob)
- Vector databases (ChromaDB, pgvector, Pinecone)

We need a pattern that:
- Allows swapping providers without changing business logic
- Supports multiple providers simultaneously (primary/fallback)
- Enables local development without external dependencies
- Facilitates testing with mocks
- Supports provider-specific configuration

## Decision
Use the **Provider Pattern** (Strategy + Factory) with interface-based abstraction.

### Core Principles

1. **Interface First**: Define abstract base classes for each provider type
2. **Factory Pattern**: Centralized provider creation with configuration
3. **Dependency Injection**: Services receive provider instances, not create them
4. **Configuration-Driven**: Provider selection via environment/config
5. **Mock-First Development**: Local mode uses mock providers by default

## Implementation

### Provider Interfaces

```python
# LLM Provider
class LLMProvider(ABC):
    @abstractmethod
    async def complete(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Return: {'text': str, 'tokens_used': int, 'estimated_cost': float}"""
        pass

# Embedding Provider
class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        pass

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        pass

# Target Agent Provider
class TargetAgentProvider(ABC):
    @abstractmethod
    async def call(self, input_text: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        pass

# Storage Provider
class StorageProvider(ABC):
    @abstractmethod
    async def upload(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        pass

    @abstractmethod
    async def download(self, key: str) -> bytes:
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        pass

    @abstractmethod
    async def generate_presigned_url(self, key: str, expiration: int = 3600) -> str:
        pass
```

### Factory Pattern

```python
class LLMProviderFactory:
    @staticmethod
    def create_provider(provider: str, model: str, api_key: str, base_url: str = "") -> LLMProvider:
        if provider == "openai":
            return OpenAIProvider(model, api_key, base_url)
        elif provider == "anthropic":
            return AnthropicProvider(model, api_key, base_url)
        elif provider == "mock" or settings.EVAL_MODE == "local":
            return MockLLMProvider()
        else:
            logger.warning("unknown_llm_provider", provider=provider)
            return MockLLMProvider()
```

### Dependency Injection

```python
# Services receive providers via constructor
class ScoringService:
    def __init__(
        self,
        judge: BaseJudge = None,  # Injected
        fallback_judge: BaseJudge = None,  # Injected
    ):
        self.judge = judge or LLMJudge()  # Creates own if not provided
        self.fallback_judge = fallback_judge or FallbackJudge()

# FastAPI dependency injection
async def get_judge() -> BaseJudge:
    return LLMJudge()  # Uses factory internally

@router.post("/score")
async def score_endpoint(judge: BaseJudge = Depends(get_judge)):
    ...
```

## Provider Implementations

### LLM Providers
| Provider | Class | Features |
|----------|-------|----------|
| OpenAI | OpenAIProvider | Chat completions, JSON mode, streaming |
| Anthropic | AnthropicProvider | Messages API, tool use |
| Google | GoogleProvider | Vertex AI, Gemini |
| Local | MockLLMProvider | Deterministic responses for testing |

### Target Agent Providers
| Provider | Class | Use Case |
|----------|-------|----------|
| HTTP | HTTPTargetAgentProvider | REST APIs with templates |
| gRPC | GRPCTargetAgentProvider | High-performance internal |
| Mock | MockTargetAgentProvider | Local dev, CI, seeded regressions |

### Storage Providers
| Provider | Class | Backend |
|----------|-------|---------|
| S3 | S3StorageProvider | AWS S3, MinIO, any S3-compatible |
| Local | LocalStorageProvider | Filesystem (dev only) |
| GCS | GCSStorageProvider | Google Cloud Storage |
| Azure | AzureBlobProvider | Azure Blob Storage |

## Configuration

```bash
# Primary Judge
PRIMARY_JUDGE_PROVIDER=openai
PRIMARY_JUDGE_MODEL=gpt-4o-2024-08-06
PRIMARY_JUDGE_API_KEY=sk-...
PRIMARY_JUDGE_BASE_URL=https://api.openai.com/v1

# Secondary Judge
SECONDARY_JUDGE_PROVIDER=anthropic
SECONDARY_JUDGE_MODEL=claude-3-5-sonnet-20241022
SECONDARY_JUDGE_API_KEY=sk-...

# Target Agent
TARGET_AGENT_DEFAULT_TIMEOUT=30
TARGET_AGENT_ALLOWED_HOSTS=api.example.com,internal.example.com
TARGET_AGENT_BLOCK_PRIVATE_IPS=true

# Storage
S3_ENDPOINT_URL=https://s3.amazonaws.com
S3_ACCESS_KEY=...
S3_SECRET_KEY=...
S3_BUCKET=redteam-artifacts
```

## Testing Benefits

### Unit Tests
```python
async def test_scoring_with_mock():
    mock_judge = MockLLMJudge()
    service = ScoringService(judge=mock_judge)
    result = await service.score_execution(...)
    assert result.verdict == Verdict.PASS
```

### Integration Tests
```python
# Use real providers with test credentials
async def test_e2e_with_real_llm():
    judge = LLMProviderFactory.create_provider("openai", "gpt-4o-mini", TEST_KEY)
    service = ScoringService(judge=judge)
    ...
```

### Local Development
```bash
# No API keys needed
EVAL_MODE=local
DEV_MOCK_TARGET_AGENT=true
DEV_MOCK_JUDGE=true
```

## Consequences

### Positive
- **Zero external deps for local dev**: Mock providers enable full offline development
- **Easy provider switching**: Change one env var to switch OpenAI → Anthropic
- **Fallback support**: Automatic fallback on primary provider failure
- **Testability**: Inject mocks at any level
- **Extensibility**: Add new providers without touching services
- **Cost control**: Mock providers have zero cost

### Negative
- **Abstraction overhead**: Slight complexity in factory/interface layer
- **Interface maintenance**: Must update all providers when interface changes
- **Provider parity**: Not all providers support all features (JSON mode, streaming)

## Migration Path

When adding a new provider:
1. Implement the interface
2. Add to factory
3. Add configuration variables
4. Add tests (unit + integration)
5. Update documentation

No changes to services, API, or domain logic required.