from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from app.api.deps import get_async_session
from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.domain.enums import RunStatus
from app.domain.matrix import (
    EvaluationCell,
    EvaluationMatrix,
    MatrixConfiguration,
    MatrixExecutionSummary,
)
from app.models.matrix import EvaluationMatrix as EvaluationMatrixModel, EvaluationMatrixCell as EvaluationMatrixCellModel
from app.models.run import Run
from app.models.target_agent import TargetAgent
from app.models.test_suite import TestCase
from app.repositories.matrix import EvaluationMatrixCellRepository, EvaluationMatrixRepository
from app.repositories.runs import ExecutionRepository, ResultRepository, RunRepository
from app.repositories.suites import TestCaseRepository, TestSuiteRepository
from app.repositories.agents import TargetAgentRepository
from app.repositories.baselines import (
    BaselineRepository,
    BaselineItemRepository,
    RegressionRepository,
    ReviewQueueRepository,
)
from app.services.execution_service import ExecutionService
from app.services.scoring_service import MockScoringService, ScoringService
from app.evaluation.gate.evaluator import GateEvaluator
from app.evaluation.regression.detector import RegressionDetector
from app.evaluation.severity.classifier import SeverityClassifier

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings

settings = get_settings()
logger = get_logger(__name__)


def get_scoring_service():
    if settings.EVAL_MODE == "local" or settings.DEV_MOCK_JUDGE:
        return MockScoringService
    return ScoringService


router = APIRouter()


@router.post("/matrices", response_model=EvaluationMatrix, status_code=201)
async def create_matrix(
    name: str,
    suite_id: UUID,
    test_case_ids: list[UUID],
    configurations: list[MatrixConfiguration],
    description: str | None = None,
    session: AsyncSession = Depends(get_async_session),
):
    """Create a new evaluation matrix."""
    matrix_repo = EvaluationMatrixRepository(session)
    cell_repo = EvaluationMatrixCellRepository(session)
    suite_repo = TestSuiteRepository(session)
    case_repo = TestCaseRepository(session)

    suite = await suite_repo.get(suite_id)
    if not suite:
        raise NotFoundError("TestSuite", str(suite_id))

    # Validate all test cases belong to suite
    for tc_id in test_case_ids:
        tc = await case_repo.get(tc_id)
        if not tc or tc.suite_id != suite_id:
            raise ValidationError(f"Test case {tc_id} not found in suite {suite_id}")

    if not configurations:
        raise ValidationError("At least one configuration is required")

    matrix = EvaluationMatrixModel(
        name=name,
        description=description,
        suite_id=suite_id,
        suite_version=suite.version,
        test_case_ids=[str(tc_id) for tc_id in test_case_ids],
        configurations=[c.model_dump() for c in configurations],
    )

    matrix = await matrix_repo.create(matrix)

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
        await cell_repo.create(cell)

    matrix.total_cells = len(cells)
    await session.flush()

    logger.info("matrix_created", matrix_id=str(matrix.id), total_cells=len(cells))
    return EvaluationMatrix.model_validate(matrix)


@router.get("/matrices", response_model=list[EvaluationMatrix])
async def list_matrices(
    suite_id: UUID | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_async_session),
):
    """List evaluation matrices."""
    matrix_repo = EvaluationMatrixRepository(session)
    filters = {}
    if suite_id:
        filters["suite_id"] = suite_id
    if status:
        filters["status"] = status
    matrices = await matrix_repo.list(filters=filters, skip=skip, limit=limit)
    return [EvaluationMatrix.model_validate(m) for m in matrices]


@router.get("/matrices/{matrix_id}", response_model=EvaluationMatrix)
async def get_matrix(
    matrix_id: UUID,
    session: AsyncSession = Depends(get_async_session),
):
    """Get evaluation matrix with cells."""
    matrix_repo = EvaluationMatrixRepository(session)
    matrix = await matrix_repo.get_with_cells(matrix_id)
    if not matrix:
        raise NotFoundError("EvaluationMatrix", str(matrix_id))
    return EvaluationMatrix.model_validate(matrix)


@router.get("/matrices/{matrix_id}/summary", response_model=MatrixExecutionSummary)
async def get_matrix_summary(
    matrix_id: UUID,
    session: AsyncSession = Depends(get_async_session),
):
    """Get execution summary for matrix."""
    matrix_repo = EvaluationMatrixRepository(session)
    cell_repo = EvaluationMatrixCellRepository(session)
    
    matrix = await matrix_repo.get_with_cells(matrix_id)
    if not matrix:
        raise NotFoundError("EvaluationMatrix", str(matrix_id))

    cells = await cell_repo.list_by_matrix(matrix_id)
    
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


@router.post("/matrices/{matrix_id}/execute", response_model=EvaluationMatrix)
async def execute_matrix(
    matrix_id: UUID,
    session: AsyncSession = Depends(get_async_session),
):
    """Execute all cells in the matrix."""
    matrix_repo = EvaluationMatrixRepository(session)
    cell_repo = EvaluationMatrixCellRepository(session)
    run_repo = RunRepository(session)
    exec_repo = ExecutionRepository(session)
    result_repo = ResultRepository(session)
    suite_repo = TestSuiteRepository(session)
    case_repo = TestCaseRepository(session)
    agent_repo = TargetAgentRepository(session)
    baseline_repo = BaselineRepository(session)
    baseline_item_repo = BaselineItemRepository(session)
    regression_repo = RegressionRepository(session)
    review_repo = ReviewQueueRepository(session)

    matrix = await matrix_repo.get_with_cells(matrix_id)
    if not matrix:
        raise NotFoundError("EvaluationMatrix", str(matrix_id))

    matrix.status = RunStatus.RUNNING
    await session.flush()

    cells = await cell_repo.list_by_matrix(matrix_id)
    
    for cell in cells:
        if cell.status != RunStatus.QUEUED:
            continue

        await _execute_cell(
            cell, matrix, session,
            run_repo, exec_repo, result_repo,
            agent_repo, case_repo,
            baseline_repo, baseline_item_repo, regression_repo, review_repo
        )

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

    await session.flush()
    logger.info("matrix_executed", matrix_id=str(matrix_id), completed=completed, failed=failed)
    return EvaluationMatrix.model_validate(matrix)


async def _execute_cell(
    cell: EvaluationMatrixCellModel,
    matrix: EvaluationMatrixModel,
    session: AsyncSession,
    run_repo: RunRepository,
    exec_repo: ExecutionRepository,
    result_repo: ResultRepository,
    agent_repo: TargetAgentRepository,
    case_repo: TestCaseRepository,
    baseline_repo: BaselineRepository,
    baseline_item_repo: BaselineItemRepository,
    regression_repo: RegressionRepository,
    review_repo: ReviewQueueRepository,
):
    """Execute a single matrix cell."""
    cell.status = RunStatus.RUNNING
    cell.started_at = datetime.utcnow()
    await session.flush()

    try:
        test_case = await case_repo.get(cell.test_case_id)
        if not test_case:
            raise NotFoundError("TestCase", str(cell.test_case_id))

        config = cell.configuration
        
        agent_id = UUID(config.get("target_agent_id")) if config.get("target_agent_id") else None
        if not agent_id:
            agents = await agent_repo.list_by_suite(matrix.suite_id)
            if not agents:
                raise ValidationError("No target agent configured for matrix cell")
            agent_id = agents[0].id

        agent = await agent_repo.get(agent_id)
        if not agent:
            raise NotFoundError("TargetAgent", str(agent_id))

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
        run = await run_repo.create(run)

        cell.run_id = run.id
        await session.flush()

        execution_service = ExecutionService(
            run_repo, exec_repo, result_repo, agent_repo, case_repo
        )
        await execution_service.execute_run(run.id)

        ScoringServiceClass = get_scoring_service()
        scoring_service = ScoringServiceClass(exec_repo, result_repo, case_repo)
        await scoring_service.score_run(run.id)

        baseline = await baseline_repo.get_active_for_suite(matrix.suite_id)
        if baseline and settings.REGRESSION_DETECTION_ENABLED:
            detector = RegressionDetector(
                result_repo, baseline_repo, baseline_item_repo, regression_repo
            )
            findings = await detector.detect_regressions(run.id, baseline.id)

            classifier = SeverityClassifier(case_repo)
            for finding in findings:
                classification = await classifier.classify(finding)
                finding.severity = classification.level

            gate_evaluator = GateEvaluator(run_repo, result_repo, regression_repo)
            gate_result = await gate_evaluator.evaluate(run.id)

            if gate_result.decision in ("BLOCK", "FAIL"):
                for finding in findings:
                    if finding.severity.value in ("critical", "high"):
                        await review_repo.create_review(
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

    finally:
        await session.flush()


@router.get("/matrices/{matrix_id}/cells", response_model=list[EvaluationCell])
async def list_matrix_cells(
    matrix_id: UUID,
    status: str | None = None,
    session: AsyncSession = Depends(get_async_session),
):
    """List cells in a matrix."""
    cell_repo = EvaluationMatrixCellRepository(session)
    cells = await cell_repo.list_by_matrix(matrix_id, status=status)
    return [EvaluationCell.model_validate(c) for c in cells]


@router.get("/matrices/{matrix_id}/cells/{cell_id}", response_model=EvaluationCell)
async def get_matrix_cell(
    matrix_id: UUID,
    cell_id: UUID,
    session: AsyncSession = Depends(get_async_session),
):
    """Get a specific matrix cell."""
    cell_repo = EvaluationMatrixCellRepository(session)
    cell = await cell_repo.get(cell_id)
    if not cell or cell.matrix_id != matrix_id:
        raise NotFoundError("EvaluationMatrixCell", str(cell_id))
    return EvaluationCell.model_validate(cell)