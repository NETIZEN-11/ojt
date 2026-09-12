from datetime import datetime
from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.evaluation.agent.tool_call_evaluator import ToolCallMetrics, ToolCallEvaluationResult

logger = get_logger(__name__)


class ToolCallEvaluator:
    async def evaluate(
        self,
        test_case_id: str,
        trajectory: list[dict[str, Any]],
        expected_tool_calls: list[dict[str, Any]],
    ) -> ToolCallEvaluationResult:
        start_time = datetime.utcnow()
        errors = []

        if not expected_tool_calls:
            return ToolCallEvaluationResult(
                test_case_id=test_case_id,
                tool_calls=[],
                overall_accuracy=1.0,
                execution_time_ms=int((datetime.utcnow() - datetime.utcnow()).total_seconds() * 1000),
                errors=[],
            )

        tool_call_metrics = []
        for i, expected in enumerate(expected_tool_calls):
            actual = trajectory[i] if i < len(trajectory) else {}

            metric = await self._evaluate_tool_call(expected, actual)
            tool_call_metrics.append(metric)

        correct = sum(1 for m in tool_call_metrics if m.correct_tool_selected and m.arguments_valid)
        overall_accuracy = correct / len(tool_call_metrics) if tool_call_metrics else 0.0

        elapsed = datetime.utcnow() - start_time
        total_time_ms = int(elapsed.total_seconds() * 1000)

        return ToolCallEvaluationResult(
            test_case_id=test_case_id,
            tool_calls=tool_call_metrics,
            overall_accuracy=overall_accuracy,
            execution_time_ms=total_time_ms,
            errors=[],
        )

    async def _evaluate_tool_call(
        self, expected: dict[str, Any], actual: dict[str, Any]
    ) -> ToolCallMetrics:
        expected_tool = expected.get("tool_name", "")
        expected_args = expected.get("arguments", {})

        actual_tool = actual.get("tool_name", "")
        actual_args = actual.get("arguments", {})
        error = actual.get("error", None)

        correct_tool = expected_tool == actual_tool

        arguments_valid = True
        for key, expected_val in expected_args.items():
            if key not in actual_args:
                arguments_valid = False
                break
            if isinstance(expected_val, dict) and isinstance(actual_args.get(key), dict):
                pass  # nested dict comparison would go here
            elif actual_args.get(key) != expected_val:
                arguments_valid = False
                break

        execution_time_ms = actual.get("execution_time_ms", 0)

        return ToolCallMetrics(
            correct_tool_selected=correct_tool,
            arguments_valid=arguments_valid,
            result_processed=error is None,
            execution_time_ms=execution_time_ms,
            error=error,
        )