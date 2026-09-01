from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List, Optional, Union
from pydantic import BaseModel
from datetime import datetime

from app.api.deps import get_db, get_review_repo, get_review_label_repo, get_regression_repo, get_current_active_user, require_role, TokenData
from app.repositories.baselines import ReviewQueueRepository, ReviewLabelRepository, RegressionRepository
from app.models.review import ReviewQueue, ReviewLabelRecord
from app.domain.enums import ReviewStatus, ReviewLabel, SeverityLevel
from app.core.exceptions import NotFoundError, ConflictError

router = APIRouter()


class ReviewLabelRequest(BaseModel):
    label: ReviewLabel
    rationale: str


class ReviewAssignRequest(BaseModel):
    assignee_id: UUID


class ReviewResponse(BaseModel):
    id: UUID
    regression_id: UUID
    run_id: UUID
    severity: SeverityLevel
    confidence: float
    category: str
    status: ReviewStatus
    assigned_to: Optional[UUID] = None
    label: Optional[ReviewLabel] = None
    reviewer_notes: Optional[str] = None
    created_at: Union[datetime, str]
    updated_at: Union[datetime, str]
    resolved_at: Optional[Union[datetime, str]] = None

    class Config:
        from_attributes = True


class ReviewLabelResponse(BaseModel):
    id: UUID
    review_id: UUID
    label: ReviewLabel
    reviewer_id: UUID
    rationale: str
    created_at: Union[datetime, str]

    class Config:
        from_attributes = True


@router.get("/", response_model=List[ReviewResponse])
async def list_reviews(
    skip: int = 0,
    limit: int = 100,
    status: Optional[ReviewStatus] = None,
    assignee_id: Optional[UUID] = None,
    review_repo: ReviewQueueRepository = Depends(get_review_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "reviewer", "ml_engineer", "qa_engineer", "viewer"])),
):
    if status:
        reviews = await review_repo.list_by_status(status, skip, limit)
    elif assignee_id:
        reviews = await review_repo.list_by_assignee(assignee_id, skip, limit)
    else:
        reviews = await review_repo.list_pending(skip, limit)
    return [ReviewResponse.model_validate(review) for review in reviews]


@router.get("/{review_id}", response_model=ReviewResponse)
async def get_review(
    review_id: UUID,
    review_repo: ReviewQueueRepository = Depends(get_review_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "reviewer", "ml_engineer", "qa_engineer", "viewer"])),
):
    review = await review_repo.get(review_id)
    if not review:
        raise NotFoundError("Review", str(review_id))
    return ReviewResponse.model_validate(review)


@router.post("/{review_id}/assign")
async def assign_review(
    review_id: UUID,
    request: ReviewAssignRequest,
    review_repo: ReviewQueueRepository = Depends(get_review_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "reviewer"])),
):
    review = await review_repo.get(review_id)
    if not review:
        raise NotFoundError("Review", str(review_id))

    review.assigned_to = request.assignee_id
    review.status = ReviewStatus.IN_REVIEW
    review.updated_at = datetime.utcnow()
    await review_repo.session.flush()

    return {"message": "Review assigned"}


@router.post("/{review_id}/label")
async def label_review(
    review_id: UUID,
    request: ReviewLabelRequest,
    review_repo: ReviewQueueRepository = Depends(get_review_repo),
    label_repo: ReviewLabelRepository = Depends(get_review_label_repo),
    regression_repo: RegressionRepository = Depends(get_regression_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "reviewer"])),
):
    review = await review_repo.get(review_id)
    if not review:
        raise NotFoundError("Review", str(review_id))

    if review.status == ReviewStatus.RESOLVED:
        raise ConflictError("Review already resolved")

    label_record = ReviewLabelRecord(
        review_id=review_id,
        label=request.label,
        reviewer_id=UUID(current_user.sub),
        rationale=request.rationale,
    )
    await label_repo.create(label_record)

    review.label = request.label
    review.status = ReviewStatus.RESOLVED
    review.reviewer_notes = request.rationale
    review.resolved_at = datetime.utcnow()
    await review_repo.session.flush()

    if request.label == ReviewLabel.CONFIRMED_REGRESSION:
        regression = await regression_repo.get(review.regression_id)
        if regression:
            regression.acknowledged = True
            regression.acknowledged_by = UUID(current_user.sub)
            regression.acknowledged_at = datetime.utcnow()
            await regression_repo.session.flush()

    return {"message": "Review labeled", "label": request.label.value}


@router.get("/{review_id}/labels", response_model=List[ReviewLabelResponse])
async def list_review_labels(
    review_id: UUID,
    label_repo: ReviewLabelRepository = Depends(get_review_label_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "reviewer", "viewer"])),
):
    labels = await label_repo.list_by_review(review_id)
    return [ReviewLabelResponse.model_validate(label) for label in labels]


@router.post("/{review_id}/escalate")
async def escalate_review(
    review_id: UUID,
    review_repo: ReviewQueueRepository = Depends(get_review_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "reviewer"])),
):
    review = await review_repo.get(review_id)
    if not review:
        raise NotFoundError("Review", str(review_id))

    review.status = ReviewStatus.ESCALATED
    review.updated_at = datetime.utcnow()
    await review_repo.session.flush()

    return {"message": "Review escalated"}