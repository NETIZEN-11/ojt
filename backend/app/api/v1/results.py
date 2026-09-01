from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import datetime
from typing import List, Optional, Union
from pydantic import BaseModel

from app.api.deps import get_db, get_result_repo, get_current_active_user, require_role, TokenData
from app.repositories.runs import ResultRepository
from app.models.run import Result
from app.domain.enums import Verdict
from app.core.exceptions import NotFoundError

router = APIRouter()


class ResultDetail(BaseModel):
    id: UUID
    execution_id: UUID
    run_id: UUID
    test_case_id: UUID
    verdict: Verdict
    confidence: float
    matcher_used: Optional[str] = None
    judge_output: Optional[dict] = None
    second_judge_output: Optional[dict] = None
    judge_agreement: Optional[bool] = False
    evidence: List[dict] = []
    execution_time_ms: int = 0
    tokens_used: int = 0
    estimated_cost: float = 0.0
    errors: List[str] = []
    created_at: Union[datetime, str]

    class Config:
        from_attributes = True


@router.get("/run/{run_id}", response_model=List[ResultDetail])
async def list_results_by_run(
    run_id: UUID,
    verdict: Optional[Verdict] = None,
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