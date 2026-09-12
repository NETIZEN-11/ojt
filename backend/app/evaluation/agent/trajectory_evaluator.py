from datetime import datetime
from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.evaluation.agent.trajectory_evaluator import TrajectoryMetrics, TrajectoryEvaluationResult

logger = get_logger(__name__)


class TrajectoryEvaluator:
    async def evaluate(
        self,
        test_case_id: str,
        trajectory: list[dict[str, Any]],
        expected_final_answer: str = "",
    ) -> TrajectoryEvaluationResult:
        start_time = datetime.utcnow()
        errors = []

        try:
            metrics = await self._evaluate_trajectory(trajectory, expected_final_answer)
        except Exception as e:
            logger.error("trajectory_metrics_failed", test_case_id=test_case_id, error=str(e))
            errors.append(f"Trajectory metrics failed: {e}")
            metrics = TrajectoryMetrics(
                step_count=0,
                valid_tool_calls=0,
                invalid_tool_calls=0,
                unauthorized_tool_calls=0,
                tool_selection_accuracy=0.0,
                argument_validity=0.0,
                trajectory_coherence=0.0,
                goal_achievement=0.0,
            )

        elapsed = datetime.utcnow() - start_time
        total_time_ms = int(elapsed.total_seconds() * 1000)

        return TrajectoryEvaluationResult(
            test_case_id=test_case_id,
            trajectory=trajectory,
            metrics=metrics,
            execution_time_ms=total_time_ms,
            errors=errors,
        )

    async def _evaluate_trajectory(
        self,
        trajectory: list[dict[str, Any]],
        expected_final_answer: str,
    ) -> TrajectoryMetrics:
        if not trajectory:
            return TrajectoryMetrics(
                step_count=0,
                valid_tool_calls=0,
                invalid_tool_calls=0,
                unauthorized_tool_calls=0,
                tool_selection_accuracy=0.0,
                argument_validity=0.0,
                trajectory_coherence=0.0,
                goal_achievement=0.0,
            )

        valid_calls = 0
        invalid_calls = 0
        unauthorized_calls = 0

        for step in trajectory:
            tool_name = step.get("tool_name", "")
            arguments = step.get("arguments", {})
            error = step.get("error", None)

            if error:
                invalid_calls += 1
                if "unauthorized" in error.lower() or "permission" in error.lower():
                    unauthorized_calls += 1
            else:
                valid_calls += 1

        total_calls = valid_calls + invalid_calls
        tool_selection_accuracy = valid_calls / total_calls if total_calls > 0 else 0.0
        argument_validity = valid_calls / total_calls if total_calls > 0 else 0.0

        trajectory_coherence = self._calculate_coherence(trajectory)

        goal_achievement = 0.0
        if trajectory:
            final_answer = trajectory[-1].get("final_answer", "")
            if expected_final_answer and final_answer:
                goal_achievement = self._compare_answers(final_answer, expected_final_answer)

        return TrajectoryMetrics(
            step_count=len(trajectory),
            valid_tool_calls=valid_calls,
            invalid_tool_calls=invalid_calls,
            unauthorized_tool_calls=unauthorized_calls,
            tool_selection_accuracy=tool_selection_accuracy,
            argument_validity=argument_validity,
            trajectory_coherence=trajectory_coherence,
            goal_achievement=goal_achievement,
        )

    def _calculate_coherence(self, trajectory: list[dict[str, Any]]) -> float:
        if len(trajectory) < 2:
            return 1.0

        coherent = 0
        for i in range(1, len(trajectory)):
            prev_result = trajectory[i - 1].get("result", "")
            curr_tool = trajectory[i].get("tool_name", "")

            if prev_result and curr_tool:
                coherent += 1

        return coherent / (len(trajectory) - 1)

    def _compare_answers(self, actual: str, expected: str) -> float:
        actual_lower = actual.lower()
        expected_lower = expected.lower()

        if expected_lower in actual_lower:
            return 1.0

        expected_words = set(expected_lower.split())
        actual_words = set(actual_lower.split())

        if not expected_words:
            return 0.0

        overlap = len(expected_words & actual_words)
        return overlap / len(expected_words)