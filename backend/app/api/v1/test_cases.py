from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import datetime
from typing import List, Optional, Union
from pydantic import BaseModel

from app.api.deps import get_db, get_case_repo, get_current_active_user, require_role, TokenData
from app.repositories.suites import TestCaseRepository
from app.models.test_suite import TestCase
from app.domain.enums import TestCaseCategory, TestCaseSeverity
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


class TestCaseCreate(BaseModel):
    test_case_id: str
    category: TestCaseCategory
    severity: TestCaseSeverity
    input: str
    expected_behavior: dict
    metadata: dict = {}


class TestCaseUpdate(BaseModel):
    category: Optional[TestCaseCategory] = None
    severity: Optional[TestCaseSeverity] = None
    input: Optional[str] = None
    expected_behavior: Optional[dict] = None
    metadata: Optional[dict] = None


class TestCaseResponse(BaseModel):
    id: UUID
    test_case_id: str
    category: TestCaseCategory
    severity: TestCaseSeverity
    input: str
    expected_behavior: dict = {}
    metadata: dict = {}
    is_active: bool

    class Config:
        from_attributes = True


def _build_case_response(c) -> TestCaseResponse:
    return TestCaseResponse(
        id=c.id,
        test_case_id=c.test_case_id,
        category=c.category,
        severity=c.severity,
        input=c.input,
        expected_behavior=c.expected_behavior or {},
        metadata=c.test_case_metadata or {},
        is_active=c.is_active,
    )


@router.get("/suite/{suite_id}", response_model=List[TestCaseResponse])
async def list_test_cases(
    suite_id: UUID,
    skip: int = 0,
    limit: int = 100,
    category: Optional[TestCaseCategory] = None,
    case_repo: TestCaseRepository = Depends(get_case_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])),
):
    if category:
        cases = await case_repo.list_by_category(suite_id, category)
    else:
        cases = await case_repo.list_by_suite(suite_id, skip, limit)
    return [_build_case_response(c) for c in cases]


@router.post("/suite/{suite_id}", response_model=TestCaseResponse, status_code=201)
async def create_test_case(
    suite_id: UUID,
    test_case: TestCaseCreate,
    case_repo: TestCaseRepository = Depends(get_case_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer"])),
):
    existing = await case_repo.get_by_suite_and_id(suite_id, test_case.test_case_id)
    if existing:
        raise HTTPException(status_code=409, detail="Test case ID already exists in this suite")

    new_case = TestCase(
        suite_id=suite_id,
        **test_case.model_dump(),
        created_by=UUID(current_user.sub),
    )
    new_case = await case_repo.create(new_case)
    return _build_case_response(new_case)


@router.get("/{case_id}", response_model=TestCaseResponse)
async def get_test_case(
    case_id: UUID,
    case_repo: TestCaseRepository = Depends(get_case_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])),
):
    case = await case_repo.get(case_id)
    if not case:
        raise NotFoundError("TestCase", str(case_id))
    return _build_case_response(case)


@router.patch("/{case_id}", response_model=TestCaseResponse)
async def update_test_case(
    case_id: UUID,
    update: TestCaseUpdate,
    case_repo: TestCaseRepository = Depends(get_case_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer"])),
):
    case = await case_repo.get(case_id)
    if not case:
        raise NotFoundError("TestCase", str(case_id))

    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "metadata":
            case.test_case_metadata = value
        else:
            setattr(case, key, value)

    await case_repo.session.flush()
    return _build_case_response(case)


@router.delete("/{case_id}")
async def delete_test_case(
    case_id: UUID,
    case_repo: TestCaseRepository = Depends(get_case_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer"])),
):
    deleted = await case_repo.delete(case_id)
    if not deleted:
        raise NotFoundError("TestCase", str(case_id))
    return {"message": "Test case deleted"}