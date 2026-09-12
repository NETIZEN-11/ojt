from datetime import datetime
from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.evaluation.agent.trajectory_evaluator import TrajectoryEvaluator
from app.evaluation.agent.tool_call_evaluator import ToolCallEvaluator

logger = get_logger(__name__)


class AgentEvaluator:
    def __init__(self):
        self.trajectory_evaluator = TrajectoryEvaluator()
        self.tool_call_evaluator = ToolCallEvaluator()

    async def evaluate(
        self,
        test_case_id: str,
        input_text: str,
        trajectory: list[dict[str, Any]],
        expected_final_answer: str = "",
        expected_tool_calls: list[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        start_time = datetime.utcnow()
        errors = []

        try:
            trajectory_result = await self.trajectory_evaluator.evaluate(
                test_case_id, trajectory, expected_final_answer
            )
        except Exception as e:
            logger.error("trajectory_evaluation_failed", test_case_id=test_case_id, error=str(e))
            errors.append(f"Trajectory evaluation failed: {e}")
            trajectory_result = {}

        try:
            tool_call_result = await self.tool_call_evaluator.evaluate(
                test_case_id, trajectory, expected_tool_calls or []
            )
        except Exception as e:
            logger.error("tool_call_evaluation_failed", test_case_id=test_case_id, error=str(e))
            errors.append(f"Tool call evaluation failed: {e}")
            tool_call_result = {}

        elapsed = datetime.utcnow() - start_time
        total_time_ms = int(elapsed.total_seconds() * 1000)

        return {
            "test_case_id": test_case_id,
            "trajectory_evaluation": trajectory_result,
            "tool_call_evaluation": tool_call_result,
            "overall_score": self._calculate_overall_score(trajectory_result, tool_call_result),
            "execution_time_ms": total_time_ms,
            "errors": errors,
        }

    def _calculate_overall_score(self, trajectory_result: dict, tool_call_result: dict) -> float:
        trajectory_score = trajectory_result.get("metrics", {}).get("goal_achievement", 0.0)
        tool_score = tool_call_result.get("overall_accuracy", 0.0)

        return trajectory_score * 0.6 + tool_score * 0.4