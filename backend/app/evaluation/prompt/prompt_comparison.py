from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PromptComparisonResult:
    prompt_a_id: str
    prompt_a_version: str
    prompt_b_id: str
    prompt_b_version: str
    winner: str
    score_difference: float
    metrics_a: dict[str, float]
    metrics_b: dict[str, float]
    cross_model_results: dict[str, Any]
    execution_time_ms: int
    errors: list[str]


class PromptComparator:
    def __init__(self):
        pass

    async def compare(
        self,
        prompt_a_id: str,
        prompt_a_version: str,
        content_a: str,
        prompt_b_id: str,
        prompt_b_version: str,
        content_b: str,
        models: list[str] = None,
        datasets: list[str] = None,
    ) -> PromptComparisonResult:
        from app.evaluation.prompt.prompt_evaluator import PromptEvaluator

        start_time = datetime.utcnow()
        errors = []

        evaluator = PromptEvaluator()

        result_a = await evaluator.evaluate(prompt_a_id, prompt_a_version, content_a)
        result_b = await evaluator.evaluate(prompt_b_id, prompt_b_version, content_b)

        metrics_a = {
            "quality": result_a.metrics.quality_score,
            "clarity": result_a.metrics.clarity_score,
            "specificity": result_a.metrics.specificity_score,
            "safety": result_a.metrics.safety_score,
            "token_efficiency": result_a.metrics.token_efficiency,
        }

        metrics_b = {
            "quality": result_b.metrics.quality_score,
            "clarity": result_b.metrics.clarity_score,
            "specificity": result_b.metrics.specificity_score,
            "safety": result_b.metrics.safety_score,
            "token_efficiency": result_b.metrics.token_efficiency,
        }

        avg_a = sum(metrics_a.values()) / len(metrics_a)
        avg_b = sum(metrics_b.values()) / len(metrics_b)

        if avg_a > avg_b:
            winner = "A"
            score_difference = avg_a - avg_b
        elif avg_b > avg_a:
            winner = "B"
            score_difference = avg_b - avg_a
        else:
            winner = "TIE"
            score_difference = 0.0

        cross_model_results = {}
        if models:
            for model in models:
                cross_model_results[model] = await self._evaluate_on_model(
                    content_a, content_b, model
                )

        elapsed = datetime.utcnow() - start_time
        total_time_ms = int(elapsed.total_seconds() * 1000)

        return PromptComparisonResult(
            prompt_a_id=prompt_a_id,
            prompt_a_version=prompt_a_version,
            prompt_b_id=prompt_b_id,
            prompt_b_version=prompt_b_version,
            winner=winner,
            score_difference=score_difference,
            metrics_a=metrics_a,
            metrics_b=metrics_b,
            cross_model_results=cross_model_results,
            execution_time_ms=total_time_ms,
            errors=errors,
        )

    async def _evaluate_on_model(
        self, content_a: str, content_b: str, model: str
    ) -> dict[str, float]:
        return {
            "model": model,
            "prompt_a_score": 0.5,
            "prompt_b_score": 0.5,
        }