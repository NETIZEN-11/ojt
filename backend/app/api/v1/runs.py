from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import datetime
from typing import List, Optional, Union
from pydantic import BaseModel

from app.api.deps import get_db, get_run_repo, get_execution_repo, get_result_repo, get_agent_repo, get_suite_repo, get_baseline_repo, get_current_active_user, require_role, TokenData
from app.repositories.runs import RunRepository, ExecutionRepository, ResultRepository
from app.repositories.agents import TargetAgentRepository
from app.repositories.suites import TestSuiteRepository
from app.repositories.baselines import BaselineRepository
from app.workers.evaluation_tasks import run_evaluation
from app.models.run import Run
from app.domain.enums import RunStatus
from app.core.exceptions import NotFoundError, ConflictError
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


class RunCreate(BaseModel):
    target_agent_id: UUID
    suite_id: UUID
    suite_version: Optional[int] = None
    baseline_id: Optional[UUID] = None


class RunResponse(BaseModel):
    id: UUID
    target_agent_id: UUID
    suite_id: UUID
    suite_version: Optional[int] = 1
    baseline_id: Optional[UUID] = None
    status: RunStatus
    framework_version: str = "1.0.0"
    total_tests: int = 0
    passed_count: int = 0
    failed_count: int = 0
    inconclusive_count: int = 0
    regression_count: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    total_cost_usd: float = 0.0
    total_latency_ms: int = 0
    started_at: Optional[Union[datetime, str]] = None
    completed_at: Optional[Union[datetime, str]] = None
    created_at: Union[datetime, str]
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/", response_model=List[RunResponse])
async def list_runs(
    skip: int = 0,
    limit: int = 100,
    target_agent_id: Optional[UUID] = None,
    suite_id: Optional[UUID] = None,
    status: Optional[RunStatus] = None,
    run_repo: RunRepository = Depends(get_run_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])),
):
    filters = {}
    if target_agent_id:
        filters["target_agent_id"] = target_agent_id
    if suite_id:
        filters["suite_id"] = suite_id
    if status:
        filters["status"] = status

    runs = await run_repo.list(skip=skip, limit=limit, filters=filters)
    return [RunResponse.model_validate(run) for run in runs]


@router.post("/", response_model=RunResponse, status_code=201)
async def create_run(
    run: RunCreate,
    background_tasks: BackgroundTasks,
    run_repo: RunRepository = Depends(get_run_repo),
    agent_repo: TargetAgentRepository = Depends(get_agent_repo),
    suite_repo: TestSuiteRepository = Depends(get_suite_repo),
    baseline_repo: BaselineRepository = Depends(get_baseline_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer"])),
):
    agent = await agent_repo.get(run.target_agent_id)
    if not agent:
        raise NotFoundError("TargetAgent", str(run.target_agent_id))

    suite = await suite_repo.get(run.suite_id)
    if not suite:
        raise NotFoundError("TestSuite", str(run.suite_id))

    baseline = None
    if run.baseline_id:
        baseline = await baseline_repo.get(run.baseline_id)
        if not baseline:
            raise NotFoundError("Baseline", str(run.baseline_id))
    else:
        baseline = await baseline_repo.get_active_for_suite(suite.id)

    new_run = Run(
        target_agent_id=run.target_agent_id,
        suite_id=run.suite_id,
        suite_version=suite.version,
        baseline_id=baseline.id if baseline else None,
        framework_version="1.0.0",
        model_versions={},
        prompt_versions={},
        config_snapshot={},
        created_by=UUID(current_user.sub),
    )
    new_run = await run_repo.create(new_run)

    background_tasks.add_task(run_evaluation.delay, str(new_run.id))

    logger.info("run_created", run_id=str(new_run.id), suite_id=str(suite.id), agent_id=str(agent.id))
    return RunResponse.model_validate(new_run)


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: UUID,
    run_repo: RunRepository = Depends(get_run_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])),
):
    run = await run_repo.get(run_id)
    if not run:
        raise NotFoundError("Run", str(run_id))
    return RunResponse.model_validate(run)


@router.post("/{run_id}/cancel")
async def cancel_run(
    run_id: UUID,
    run_repo: RunRepository = Depends(get_run_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer"])),
):
    run = await run_repo.get(run_id)
    if not run:
        raise NotFoundError("Run", str(run_id))

    if run.status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED):
        raise ConflictError(f"Cannot cancel run in status {run.status}")

    run.status = RunStatus.CANCELLED
    run.completed_at = datetime.utcnow()
    await run_repo.session.flush()

    return {"message": "Run cancelled"}


@router.get("/{run_id}/executions")
async def list_executions(
    run_id: UUID,
    execution_repo: ExecutionRepository = Depends(get_execution_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])),
):
    executions = await execution_repo.list_by_run(run_id)
    return [{"id": str(e.id), "test_case_id": str(e.test_case_id), "status": e.status.value, "latency_ms": e.latency_ms} for e in executions]


@router.get("/{run_id}/results")
async def list_results(
    run_id: UUID,
    result_repo: ResultRepository = Depends(get_result_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])),
):
    results = await result_repo.list_by_run(run_id)
    return [
        {
            "id": str(r.id),
            "test_case_id": str(r.test_case_id),
            "verdict": r.verdict.value,
            "confidence": r.confidence,
            "execution_time_ms": r.execution_time_ms,
        }
        for r in results
    ]