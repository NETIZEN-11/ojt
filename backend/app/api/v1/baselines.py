from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import datetime
from typing import List, Optional, Union
from pydantic import BaseModel
from datetime import datetime

from app.api.deps import get_db, get_baseline_repo, get_baseline_item_repo, get_current_active_user, require_role, TokenData
from app.repositories.baselines import BaselineRepository, BaselineItemRepository
from app.models.baseline import Baseline, BaselineItem
from app.domain.enums import Verdict
from app.core.exceptions import NotFoundError, ConflictError

router = APIRouter()


class BaselineCreate(BaseModel):
    suite_id: UUID
    suite_version: int
    run_id: UUID
    name: str
    description: Optional[str] = None


class BaselineResponse(BaseModel):
    id: UUID
    suite_id: UUID
    suite_version: int
    run_id: UUID
    name: str
    description: Optional[str] = None
    framework_version: str = "1.0.0"
    model_versions: dict = {}
    prompt_versions: dict = {}
    approved_by: Optional[UUID] = None
    approved_at: Optional[Union[datetime, str]] = None
    is_active: bool = False
    created_at: Union[datetime, str]

    class Config:
        from_attributes = True


class BaselineItemResponse(BaseModel):
    id: UUID
    baseline_id: UUID
    test_case_id: UUID
    verdict: Verdict
    confidence: float
    evidence: List[dict]

    class Config:
        from_attributes = True


@router.get("/", response_model=List[BaselineResponse])
async def list_baselines(
    skip: int = 0,
    limit: int = 100,
    suite_id: Optional[UUID] = None,
    baseline_repo: BaselineRepository = Depends(get_baseline_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])),
):
    filters = {}
    if suite_id:
        filters["suite_id"] = suite_id
    baselines = await baseline_repo.list(skip=skip, limit=limit, filters=filters)
    return [BaselineResponse.model_validate(b) for b in baselines]


@router.post("/", response_model=BaselineResponse, status_code=201)
async def create_baseline(
    baseline: BaselineCreate,
    baseline_repo: BaselineRepository = Depends(get_baseline_repo),
    baseline_item_repo: BaselineItemRepository = Depends(get_baseline_item_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer"])),
):
    existing = await baseline_repo.get_by_suite_version(baseline.suite_id, baseline.suite_version)
    if existing:
        raise ConflictError("Baseline already exists for this suite version")

    new_baseline = Baseline(
        **baseline.model_dump(),
        framework_version="1.0.0",
        model_versions={},
        prompt_versions={},
        approved_by=UUID(current_user.sub),
        approved_at=datetime.utcnow(),
    )
    new_baseline = await baseline_repo.create(new_baseline)

    run = new_baseline.run
    if run:
        results = run.results
        for result in results:
            item = BaselineItem(
                baseline_id=new_baseline.id,
                test_case_id=result.test_case_id,
                verdict=result.verdict,
                confidence=result.confidence,
                evidence=result.evidence,
            )
            await baseline_item_repo.create(item)

    return BaselineResponse.model_validate(new_baseline)


@router.get("/suite/{suite_id}/active", response_model=Optional[BaselineResponse])
async def get_active_baseline(
    suite_id: UUID,
    baseline_repo: BaselineRepository = Depends(get_baseline_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])),
):
    baseline = await baseline_repo.get_active_for_suite(suite_id)
    if not baseline:
        return None
    return BaselineResponse.model_validate(baseline)


@router.get("/{baseline_id}", response_model=BaselineResponse)
async def get_baseline(
    baseline_id: UUID,
    baseline_repo: BaselineRepository = Depends(get_baseline_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])),
):
    baseline = await baseline_repo.get(baseline_id)
    if not baseline:
        raise NotFoundError("Baseline", str(baseline_id))
    return BaselineResponse.model_validate(baseline)


@router.get("/{baseline_id}/items", response_model=List[BaselineItemResponse])
async def list_baseline_items(
    baseline_id: UUID,
    baseline_item_repo: BaselineItemRepository = Depends(get_baseline_item_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])),
):
    items = await baseline_item_repo.list_by_baseline(baseline_id)
    return [BaselineItemResponse.model_validate(item) for item in items]


@router.post("/{baseline_id}/approve")
async def approve_baseline(
    baseline_id: UUID,
    baseline_repo: BaselineRepository = Depends(get_baseline_repo),
    current_user: TokenData = Depends(require_role(["admin"])),
):
    baseline = await baseline_repo.get(baseline_id)
    if not baseline:
        raise NotFoundError("Baseline", str(baseline_id))

    if baseline.is_active:
        raise ConflictError("Baseline already approved")

    baseline.is_active = True
    baseline.approved_by = UUID(current_user.sub)
    baseline.approved_at = datetime.utcnow()
    await baseline_repo.session.flush()

    return {"message": "Baseline approved"}


@router.post("/{baseline_id}/deactivate")
async def deactivate_baseline(
    baseline_id: UUID,
    baseline_repo: BaselineRepository = Depends(get_baseline_repo),
    current_user: TokenData = Depends(require_role(["admin"])),
):
    baseline = await baseline_repo.get(baseline_id)
    if not baseline:
        raise NotFoundError("Baseline", str(baseline_id))

    baseline.is_active = False
    await baseline_repo.session.flush()

    return {"message": "Baseline deactivated"}