from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class CostCategory(str, Enum):
    LLM_INFERENCE = "llm_inference"
    EMBEDDING = "embedding"
    JUDGE = "judge"
    RED_TEAM = "red_team"
    RETRIEVAL = "retrieval"
    VECTOR_STORE = "vector_store"
    STORAGE = "storage"
    COMPUTE = "compute"


@dataclass
class CostEntry:
    id: UUID = field(default_factory=uuid4)
    run_id: UUID | None = None
    test_case_id: UUID | None = None
    category: CostCategory = CostCategory.LLM_INFERENCE
    provider: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    currency: str = "USD"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CostSummary:
    total_cost_usd: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    by_category: dict[str, float] = field(default_factory=dict)
    by_provider: dict[str, float] = field(default_factory=dict)
    by_model: dict[str, float] = field(default_factory=dict)
    by_run: dict[str, float] = field(default_factory=dict)
    period_start: datetime = field(default_factory=datetime.utcnow)
    period_end: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CostBreakdown:
    run_id: UUID
    run_name: str
    total_cost_usd: float
    entries: list[dict[str, Any]] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CostTrend:
    date: str
    cost_usd: float
    token_count: int
    request_count: int
