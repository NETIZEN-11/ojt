from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import TokenData, get_result_repo, require_role
from app.core.exceptions import NotFoundError
from app.domain.enums import Verdict
from app.repositories.runs import ResultRepository

router = APIRouter()


class ResultDetail(BaseModel):
    id: UUID
    execution_id: UUID
    run_id: UUID
    test_case_id: UUID
    verdict: Verdict
    confidence: float
    matcher_used: str | None = None
    judge_output: dict | None = None
    second_judge_output: dict | None = None
    judge_agreement: bool | None = False
    evidence: list[dict] = []
    execution_time_ms: int = 0
    tokens_used: int = 0
    estimated_cost: float = 0.0
    errors: list[str] = []
    created_at: datetime | str

    class Config:
        from_attributes = True


@router.get("/run/{run_id}", response_model=list[ResultDetail])
async def list_results_by_run(
    run_id: UUID,
    verdict: Verdict | None = None,
    result_repo: ResultRepository = Depends(get_result_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])),
):
    if verdict:
        results = await result_repo.list_by_run_and_verdict(run_id, verdict)
    else:
        results = await result_repo.list_by_run(run_id)
    return [ResultDetail.model_validate(result) for result in results]


@router.get("/{result_id}", response_model=ResultDetail)
async def get_result(
    result_id: UUID,
    result_repo: ResultRepository = Depends(get_result_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])),
):
    result = await result_repo.get(result_id)
    if not result:
        raise NotFoundError("Result", str(result_id))
    return ResultDetail.model_validate(result)
