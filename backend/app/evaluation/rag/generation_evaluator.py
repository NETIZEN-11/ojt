from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass
class GenerationMetrics:
    faithfulness: float
    answer_relevance: float
    context_recall: float
    context_precision: float
    factuality: float
    hallucination_rate: float


@dataclass
class GenerationEvaluationResult:
    test_case_id: str
    query: str
    answer: str
    context: list[str]
    metrics: GenerationMetrics
    execution_time_ms: int
    errors: list[str]