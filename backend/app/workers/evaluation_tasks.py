import asyncio
from datetime import datetime
from uuid import UUID

from celery import shared_task

from app.core.config import get_settings
from app.core.database import get_async_session
from app.core.logging import get_logger
from app.domain.enums import RunStatus
from app.evaluation.gate.evaluator import GateEvaluator
from app.evaluation.regression.detector import RegressionDetector
from app.evaluation.severity.classifier import SeverityClassifier
from app.repositories.agents import TargetAgentRepository
from app.repositories.baselines import (
    BaselineItemRepository,
    BaselineRepository,
    RegressionRepository,
    ReviewQueueRepository,
)
from app.repositories.runs import ExecutionRepository, ResultRepository, RunRepository
from app.repositories.suites import TestCaseRepository
from app.services.execution_service import ExecutionService
from app.services.scoring_service import MockScoringService, ScoringService

settings = get_settings()
logger = get_logger(__name__)


def get_scoring_service():
    if settings.EVAL_MODE == "local" or settings.DEV_MOCK_JUDGE:
        return MockScoringService
    return ScoringService


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_evaluation(self, run_id: str):
    run_uuid = UUID(run_id)
    logger.info("evaluation_task_started", run_id=run_id)

    async def _run():
        async with get_async_session() as session:
            run_repo = RunRepository(session)
            execution_repo = ExecutionRepository(session)
            result_repo = ResultRepository(session)
            agent_repo = TargetAgentRepository(session)
            case_repo = TestCaseRepository(session)
            baseline_repo = BaselineRepository(session)
            baseline_item_repo = BaselineItemRepository(session)
            regression_repo = RegressionRepository(session)
            review_repo = ReviewQueueRepository(session)

            run = await run_repo.get(run_uuid)
            if not run:
                logger.error("run_not_found", run_id=run_id)
                return

            try:
                execution_service = ExecutionService(
                    run_repo, execution_repo, result_repo, agent_repo, case_repo
                )
                await execution_service.execute_run(run_uuid)

                ScoringServiceClass = get_scoring_service()
                scoring_service = ScoringServiceClass(execution_repo, result_repo, case_repo)
                await scoring_service.score_run(run_uuid)

                baseline = await baseline_repo.get_active_for_suite(run.suite_id)
                if baseline and settings.REGRESSION_DETECTION_ENABLED:
                    detector = RegressionDetector(
                        result_repo, baseline_repo, baseline_item_repo, regression_repo
                    )
                    findings = await detector.detect_regressions(run_uuid, baseline.id)

                    classifier = SeverityClassifier(case_repo)
                    for finding in findings:
                        classification = await classifier.classify(finding)
                        finding.severity = classification.level

                    gate_evaluator = GateEvaluator(run_repo, result_repo, regression_repo)
                    gate_result = await gate_evaluator.evaluate(run_uuid)

                    if gate_result.decision in ("BLOCK", "FAIL"):
                        for finding in findings:
                            if finding.severity.value in ("critical", "high"):
                                review = await review_repo.create_review(
                                    regression_id=finding.test_case_id,
                                    run_id=run_uuid,
                                    severity=finding.severity,
                                    confidence=0.8,
                                    category="regression",
                                )
                                logger.info("review_created", review_id=str(review.id))

                logger.info("evaluation_task_completed", run_id=run_id)

            except Exception as e:
                logger.error("evaluation_task_failed", run_id=run_id, error=str(e))
                run = await run_repo.get(run_uuid)
                if run:
                    run.status = RunStatus.FAILED
                    run.error_message = str(e)
                    run.completed_at = datetime.utcnow()
                    await session.flush()
                raise

    asyncio.run(_run())


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def run_seeded_regression_benchmark(self):
    logger.info("seeded_regression_benchmark_started")

    async def _run():
        from scripts.run_seeded_regression import run_seeded_regression

        result = await run_seeded_regression()
        logger.info("seeded_regression_benchmark_completed", result=result)
        return result

    return asyncio.run(_run())


@shared_task
def cleanup_old_runs(days: int = 365):
    logger.info("cleanup_old_runs_started", days=days)
    # Implementation would delete old runs, transcripts, etc.
    logger.info("cleanup_old_runs_completed")


@shared_task
def check_cost_limits():
    logger.info("cost_limit_check_started")
    # Implementation would check daily/run cost limits
    logger.info("cost_limit_check_completed")
