from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import (
    TokenData,
    get_regression_repo,
    get_review_label_repo,
    get_review_repo,
    get_result_repo,
    require_role,
)
from app.core.exceptions import ConflictError, NotFoundError
from app.domain.enums import ReviewLabel, ReviewStatus, SeverityLevel
from app.models.review import ReviewLabelRecord
from app.repositories.baselines import (
    RegressionRepository,
    ReviewLabelRepository,
    ReviewQueueRepository,
)
from app.repositories.runs import ResultRepository

router = APIRouter()


class ReviewLabelRequest(BaseModel):
    label: ReviewLabel
    rationale: str


class ReviewAssignRequest(BaseModel):
    assignee_id: UUID


class ReviewUpdateRequest(BaseModel):
    label: ReviewLabel | None = None
    notes: str | None = None


class EvidenceItem(BaseModel):
    source: str
    text: str
    metadata: dict[str, Any] = {}


class ReviewResponse(BaseModel):
    id: UUID
    regression_id: UUID
    run_id: UUID
    severity: SeverityLevel
    confidence: float
    category: str
    status: ReviewStatus
    assigned_to: UUID | None = None
    label: ReviewLabel | None = None
    reviewer_notes: str | None = None
    created_at: datetime | str
    updated_at: datetime | str
    resolved_at: datetime | str | None = None
    evidence: list[EvidenceItem] = []
    test_case_input: str | None = None
    test_case_expected: str | None = None
    actual_response: str | None = None
    judge_output: dict[str, Any] | None = None

    class Config:
        from_attributes = True


class ReviewLabelResponse(BaseModel):
    id: UUID
    review_id: UUID
    label: ReviewLabel
    reviewer_id: UUID
    rationale: str
    created_at: datetime | str

    class Config:
        from_attributes = True


@router.get("/", response_model=list[ReviewResponse])
async def list_reviews(
    skip: int = 0,
    limit: int = 100,
    status: ReviewStatus | None = None,
    assignee_id: UUID | None = None,
    review_repo: ReviewQueueRepository = Depends(get_review_repo),
    current_user: TokenData = Depends(
        require_role(
            ["admin", "safety_engineer", "reviewer", "ml_engineer", "qa_engineer", "viewer"]
        )
    ),
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
    result_repo: ResultRepository = Depends(get_result_repo),
    regression_repo: RegressionRepository = Depends(get_regression_repo),
    current_user: TokenData = Depends(
        require_role(
            ["admin", "safety_engineer", "reviewer", "ml_engineer", "qa_engineer", "viewer"]
        )
    ),
):
    review = await review_repo.get(review_id)
    if not review:
        raise NotFoundError("Review", str(review_id))

    # Enrich with evidence and regression details
    evidence = review.evidence if review.evidence else []
    test_case_input = None
    test_case_expected = None
    actual_response = None
    judge_output = None

    if review.regression_id:
        regression = await regression_repo.get(review.regression_id)
        if regression:
            evidence.extend(regression.evidence or [])
            
            # Get the result for more details
            result = await result_repo.get_by_run_and_test_case(review.run_id, regression.test_case_id)
            if result:
                test_case_input = result.test_case.input if result.test_case else None
                actual_response = result.judge_output.get("response", "") if result.judge_output else None
                judge_output = result.judge_output
                if regression.test_case:
                    test_case_expected = regression.test_case.input

    return ReviewResponse(
        id=review.id,
        regression_id=review.regression_id,
        run_id=review.run_id,
        severity=review.severity,
        confidence=review.confidence,
        category=review.category,
        status=review.status,
        assigned_to=review.assigned_to,
        label=review.label,
        reviewer_notes=review.reviewer_notes,
        created_at=review.created_at,
        updated_at=review.updated_at,
        resolved_at=review.resolved_at,
        evidence=evidence,
        test_case_input=test_case_input,
        test_case_expected=test_case_expected,
        actual_response=actual_response,
        judge_output=judge_output,
    )


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


@router.get("/{review_id}/labels", response_model=list[ReviewLabelResponse])
async def list_review_labels(
    review_id: UUID,
    label_repo: ReviewLabelRepository = Depends(get_review_label_repo),
    current_user: TokenData = Depends(
        require_role(["admin", "safety_engineer", "reviewer", "viewer"])
    ),
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


@router.patch("/{review_id}")
async def update_review(
    review_id: UUID,
    update: ReviewUpdateRequest,
    review_repo: ReviewQueueRepository = Depends(get_review_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "reviewer"])),
):
    review = await review_repo.get(review_id)
    if not review:
        raise NotFoundError("Review", str(review_id))

    if update.notes is not None:
        review.reviewer_notes = update.notes
    if update.label is not None:
        review.label = update.label
        if update.label in (
            ReviewLabel.CONFIRMED_REGRESSION,
            ReviewLabel.FALSE_POSITIVE,
            ReviewLabel.NON_BLOCKING,
        ):
            review.status = ReviewStatus.RESOLVED
            review.resolved_at = datetime.utcnow()
    review.updated_at = datetime.utcnow()
    await review_repo.session.flush()

    return {"message": "Review updated"}
