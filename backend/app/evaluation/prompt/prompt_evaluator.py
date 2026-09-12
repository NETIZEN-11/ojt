from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PromptMetrics:
    quality_score: float
    clarity_score: float
    specificity_score: float
    safety_score: float
    token_efficiency: float


@dataclass
class PromptEvaluationResult:
    prompt_id: str
    prompt_version: str
    content: str
    metrics: PromptMetrics
    execution_time_ms: int
    errors: list[str]


class PromptEvaluator:
    def __init__(self):
        pass

    async def evaluate(
        self,
        prompt_id: str,
        prompt_version: str,
        content: str,
        test_cases: list[dict[str, Any]] = None,
    ) -> PromptEvaluationResult:
        start_time = datetime.utcnow()
        errors = []

        try:
            quality_score = await self._evaluate_quality(content)
            clarity_score = await self._evaluate_clarity(content)
            specificity_score = await self._evaluate_specificity(content)
            safety_score = await self._evaluate_safety(content)
            token_efficiency = await self._evaluate_token_efficiency(content)

            metrics = PromptMetrics(
                quality_score=quality_score,
                clarity_score=clarity_score,
                specificity_score=specificity_score,
                safety_score=safety_score,
                token_efficiency=token_efficiency,
            )
        except Exception as e:
            logger.error("prompt_metrics_failed", prompt_id=prompt_id, error=str(e))
            errors.append(f"Prompt metrics failed: {e}")
            metrics = PromptMetrics(
                quality_score=0.0,
                clarity_score=0.0,
                specificity_score=0.0,
                safety_score=0.0,
                token_efficiency=0.0,
            )

        elapsed = datetime.utcnow() - start_time
        total_time_ms = int(elapsed.total_seconds() * 1000)

        return PromptEvaluationResult(
            prompt_id=prompt_id,
            prompt_version=prompt_version,
            content=content,
            metrics=metrics,
            execution_time_ms=total_time_ms,
            errors=errors,
        )

    async def _evaluate_quality(self, content: str) -> float:
        score = 0.5

        if len(content) > 50:
            score += 0.1
        if len(content) > 200:
            score += 0.1

        if "{" in content and "}" in content:
            score += 0.1

        if any(word in content.lower() for word in ["please", "must", "should", "ensure"]):
            score += 0.1

        return min(score, 1.0)

    async def _evaluate_clarity(self, content: str) -> float:
        import re

        sentences = re.split(r"[.!?]+", content)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return 0.0

        avg_length = sum(len(s.split()) for s in sentences) / len(sentences)

        if avg_length < 20:
            return 0.9
        elif avg_length < 30:
            return 0.7
        else:
            return 0.5

    async def _evaluate_specificity(self, content: str) -> float:
        specific_indicators = [
            "example",
            "format",
            "must",
            "exactly",
            "only",
            "include",
            "exclude",
            "constraint",
        ]

        content_lower = content.lower()
        matches = sum(1 for indicator in specific_indicators if indicator in content_lower)

        return min(matches / len(specific_indicators), 1.0)

    async def _evaluate_safety(self, content: str) -> float:
        unsafe_indicators = [
            "ignore",
            "bypass",
            "override",
            "disregard",
            "pretend",
            "roleplay",
            "act as",
            "you are now",
        ]

        content_lower = content.lower()
        unsafe_count = sum(1 for indicator in unsafe_indicators if indicator in content_lower)

        return max(1.0 - (unsafe_count * 0.15), 0.0)

    async def _evaluate_token_efficiency(self, content: str) -> float:
        token_estimate = len(content) / 4

        if token_estimate < 100:
            return 1.0
        elif token_estimate < 500:
            return 0.8
        elif token_estimate < 1000:
            return 0.6
        else:
            return 0.4