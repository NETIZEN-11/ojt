from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select

from app.core.config import get_settings
from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.domain.enums import RunStatus
from app.domain.matrix import EvaluationCell, EvaluationMatrix, MatrixConfiguration, MatrixExecutionSummary
from app.models.matrix import EvaluationMatrix as EvaluationMatrixModel, EvaluationMatrixCell as EvaluationMatrixCellModel
from app.models.run import Run
from app.models.target_agent import TargetAgent
from app.models.test_suite import TestCase
from app.repositories.matrix import EvaluationMatrixCellRepository, EvaluationMatrixRepository
from app.repositories.runs import RunRepository
from app.repositories.suites import TestCaseRepository, TestSuiteRepository
from app.repositories.agents import TargetAgentRepository
from app.services.execution_service import ExecutionService
from app.services.scoring_service import MockScoringService, ScoringService
from app.evaluation.gate.evaluator import GateEvaluator
from app.evaluation.regression.detector import RegressionDetector
from app.evaluation.severity.classifier import SeverityClassifier
from app.repositories.baselines import (
    BaselineRepository,
    BaselineItemRepository,
    RegressionRepository,
    ReviewQueueRepository,
)

settings = get_settings()
logger = get_logger(__name__)


def get_scoring_service():
    if settings.EVAL_MODE == "local" or settings.DEV_MOCK_JUDGE:
        return MockScoringService
    return ScoringService


class MatrixService:
    def __init__(
        self,
        matrix_repo: EvaluationMatrixRepository,
        cell_repo: EvaluationMatrixCellRepository,
        run_repo: RunRepository,
        suite_repo: TestSuiteRepository,
        case_repo: TestCaseRepository,
        agent_repo: TargetAgentRepository,
        baseline_repo: BaselineRepository,
        baseline_item_repo: BaselineItemRepository,
        regression_repo: RegressionRepository,
        review_repo: ReviewQueueRepository,
    ):
        self.matrix_repo = matrix_repo
        self.cell_repo = cell_repo
        self.run_repo = run_repo
        self.suite_repo = suite_repo
        self.case_repo = case_repo
        self.agent_repo = agent_repo
        self.baseline_repo = baseline_repo
        self.baseline_item_repo = baseline_item_repo
        self.regression_repo = regression_repo
        self.review_repo = review_repo

    async def create_matrix(
        self,
        name: str,
        suite_id: UUID,
        test_case_ids: list[UUID],
        configurations: list[MatrixConfiguration],
        description: str | None = None,
        created_by: UUID | None = None,
    ) -> EvaluationMatrix:
        """Create a new evaluation matrix."""
        suite = await self.suite_repo.get(suite_id)
        if not suite:
            raise NotFoundError("TestSuite", str(suite_id))

        # Validate all test cases belong to suite
        for tc_id in test_case_ids:
            tc = await self.case_repo.get(tc_id)
            if not tc or tc.suite_id != suite_id:
                raise ValidationError(f"Test case {tc_id} not found in suite {suite_id}")

        # Validate configurations
        if not configurations:
            raise ValidationError("At least one configuration is required")

        for config in configurations:
            # Verify model config exists if specified
            if config.model_id:
                from app.repositories.settings import ModelConfigRepository
                model_repo = ModelConfigRepository(self.matrix_repo.session)
                model = await model_repo.get(UUID(config.model_id))
                if not model:
                    raise ValidationError(f"Model config {config.model_id} not found")

            # Verify prompt version exists if specified
            if config.prompt_version_id:
                from app.repositories.settings import PromptVersionRepository
                prompt_repo = PromptVersionRepository(self.matrix_repo.session)
                prompt = await prompt_repo.get(config.prompt_version_id)
                if not prompt:
                    raise ValidationError(f"Prompt version {config.prompt_version_id} not found")

        matrix = EvaluationMatrixModel(
            name=name,
            description=description,
            suite_id=suite_id,
            suite_version=suite.version,
            test_case_ids=[str(tc_id) for tc_id in test_case_ids],
            configurations=[c.model_dump() for c in configurations],
            created_by=created_by,
        )

        matrix = await self.matrix_repo.create(matrix)

        # Build cells
        cells = []
        for tc_id in test_case_ids:
            for config in configurations:
                cell = EvaluationMatrixCellModel(
                    matrix_id=matrix.id,
                    test_case_id=tc_id,
                    configuration=config.model_dump(),
                )
                cells.append(cell)

        for cell in cells:
            await self.cell_repo.create(cell)

        matrix.total_cells = len(cells)
        await self.matrix_repo.session.flush()

        logger.info("matrix_created", matrix_id=str(matrix.id), total_cells=len(cells))
        return EvaluationMatrix.model_validate(matrix)

    async def get_matrix(self, matrix_id: UUID) -> EvaluationMatrix | None:
        """Get matrix with cells."""
        matrix_model = await self.matrix_repo.get_with_cells(matrix_id)
        if not matrix_model:
            return None
        return EvaluationMatrix.model_validate(matrix_model)

    async def get_matrix_summary(self, matrix_id: UUID) -> MatrixExecutionSummary | None:
        """Get execution summary for matrix."""
        matrix = await self.get_matrix(matrix_id)
        if not matrix:
            return None

        cells = await self.cell_repo.list_by_matrix(matrix_id)
        
        completed = sum(1 for c in cells if c.status == RunStatus.COMPLETED)
        failed = sum(1 for c in cells if c.status in (RunStatus.FAILED, RunStatus.CANCELLED))
        queued = sum(1 for c in cells if c.status == RunStatus.QUEUED)
        running = sum(1 for c in cells if c.status == RunStatus.RUNNING)

        if failed > 0 and completed + failed == len(cells):
            overall = RunStatus.FAILED
        elif completed == len(cells):
            overall = RunStatus.COMPLETED
        elif running > 0 or queued < len(cells):
            overall = RunStatus.RUNNING
        else:
            overall = RunStatus.QUEUED

        return MatrixExecutionSummary(
            matrix_id=matrix_id,
            total_cells=len(cells),
            completed_cells=completed,
            failed_cells=failed,
            queued_cells=queued,
            running_cells=running,
            overall_status=overall,
            cells=[EvaluationCell.model_validate(c) for c in cells],
        )

    async def execute_matrix(self, matrix_id: UUID) -> EvaluationMatrix:
        """Execute all cells in the matrix."""
        matrix = await self.matrix_repo.get_with_cells(matrix_id)
        if not matrix:
            raise NotFoundError("EvaluationMatrix", str(matrix_id))

        matrix.status = RunStatus.RUNNING
        await self.matrix_repo.session.flush()

        cells = await self.cell_repo.list_by_matrix(matrix_id)
        
        for cell in cells:
            if cell.status != RunStatus.QUEUED:
                continue

            await self._execute_cell(cell, matrix)

        # Update matrix status
        completed = sum(1 for c in cells if c.status == RunStatus.COMPLETED)
        failed = sum(1 for c in cells if c.status in (RunStatus.FAILED, RunStatus.CANCELLED))
        
        matrix.completed_cells = completed
        matrix.failed_cells = failed
        
        if failed > 0 and completed + failed == len(cells):
            matrix.status = RunStatus.FAILED
        elif completed == len(cells):
            matrix.status = RunStatus.COMPLETED
        else:
            matrix.status = RunStatus.RUNNING

        await self.matrix_repo.session.flush()
        logger.info("matrix_executed", matrix_id=str(matrix_id), completed=completed, failed=failed)
        return EvaluationMatrix.model_validate(matrix)

    async def _execute_cell(self, cell: EvaluationMatrixCellModel, matrix: EvaluationMatrixModel):
        """Execute a single matrix cell."""
        cell.status = RunStatus.RUNNING
        cell.started_at = datetime.utcnow()
        await self.cell_repo.session.flush()

        try:
            # Get test case
            test_case = await self.case_repo.get(cell.test_case_id)
            if not test_case:
                raise NotFoundError("TestCase", str(cell.test_case_id))

            # Create a run for this cell
            config = cell.configuration
            
            # Get target agent from configuration or use default
            agent_id = UUID(config.get("target_agent_id")) if config.get("target_agent_id") else None
            if not agent_id:
                # Get default agent for suite
                agents = await self.agent_repo.list_by_suite(matrix.suite_id)
                if not agents:
                    raise ValidationError("No target agent configured for matrix cell")
                agent_id = agents[0].id

            agent = await self.agent_repo.get(agent_id)
            if not agent:
                raise NotFoundError("TargetAgent", str(agent_id))

            # Create run
            run = Run(
                target_agent_id=agent.id,
                suite_id=matrix.suite_id,
                suite_version=matrix.suite_version,
                framework_version="1.0.0",
                model_versions={config.get("model_provider", ""): config.get("model_id", "")},
                prompt_versions={},
                config_snapshot={
                    "matrix_id": str(matrix.id),
                    "cell_id": str(cell.id),
                    "configuration": config,
                },
                matrix_id=matrix.id,
                created_by=matrix.created_by,
            )
            run = await self.run_repo.create(run)

            # Link cell to run
            cell.run_id = run.id
            await self.cell_repo.session.flush()

            # Execute the run
            execution_service = ExecutionService(
                self.run_repo,
                self.cell_repo.session.get_bind().__class__.__bases__[0]().__class__.__dict__['execution_repo'].__self__,  # This needs fixing
                None,  # Will be created in execution_service
                self.agent_repo,
                self.case_repo,
            )
            # We need to create proper repositories for this run
            from app.repositories.runs import ExecutionRepository, ResultRepository
            exec_repo = ExecutionRepository(self.cell_repo.session)
            result_repo = ResultRepository(self.cell_repo.session)
            
            execution_service = ExecutionService(
                self.run_repo, exec_repo, result_repo, self.agent_repo, self.case_repo
            )
            await execution_service.execute_run(run.id)

            # Score the run
            ScoringServiceClass = get_scoring_service()
            scoring_service = ScoringServiceClass(exec_repo, result_repo, self.case_repo)
            await scoring_service.score_run(run.id)

            # Check for baseline and detect regressions
            baseline = await self.baseline_repo.get_active_for_suite(matrix.suite_id)
            if baseline and settings.REGRESSION_DETECTION_ENABLED:
                detector = RegressionDetector(
                    result_repo, self.baseline_repo, self.baseline_item_repo, self.regression_repo
                )
                findings = await detector.detect_regressions(run.id, baseline.id)

                classifier = SeverityClassifier(self.case_repo)
                for finding in findings:
                    classification = await classifier.classify(finding)
                    finding.severity = classification.level

                gate_evaluator = GateEvaluator(self.run_repo, result_repo, self.regression_repo)
                gate_result = await gate_evaluator.evaluate(run.id)

                if gate_result.decision in ("BLOCK", "FAIL"):
                    for finding in findings:
                        if finding.severity.value in ("critical", "high"):
                            await self.review_repo.create_review(
                                regression_id=UUID(finding.test_case_id),
                                run_id=run.id,
                                severity=finding.severity,
                                confidence=0.8,
                                category="regression",
                            )

            cell.status = RunStatus.COMPLETED
            cell.completed_at = datetime.utcnow()

        except Exception as e:
            logger.error("cell_execution_failed", cell_id=str(cell.id), error=str(e))
            cell.status = RunStatus.FAILED
            cell.completed_at = datetime.utcnow()
            cell.error_message = str(e)
            raise

        finally:
            await self.cell_repo.session.flush()