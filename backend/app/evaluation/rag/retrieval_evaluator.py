from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass
class RetrievalMetrics:
    relevant_docs: int
    retrieved_docs: int
    precision: float
    recall: float
    f1_score: float
    mrr: float
    ndcg: float


@dataclass
class RetrievalEvaluationResult:
    test_case_id: str
    query: str
    retrieved_docs: list[dict[str, Any]]
    ground_truth_docs: list[str]
    metrics: RetrievalMetrics
    execution_time_ms: int
    errors: list[str]


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