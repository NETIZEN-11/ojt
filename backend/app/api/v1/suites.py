from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import datetime
from typing import List, Optional, Union
from pydantic import BaseModel

from app.api.deps import get_db, get_suite_repo, get_case_repo, get_current_active_user, require_role, TokenData
from app.repositories.suites import TestSuiteRepository, TestCaseRepository
from app.services.suite_service import SuiteService
from app.models.test_suite import TestSuite, TestCase
from app.domain.enums import TestCaseCategory, TestCaseSeverity
from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


def _build_case_response(c) -> "TestCaseResponse":
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


class TestCaseResponse(BaseModel):
    id: UUID
    test_case_id: str
    category: TestCaseCategory
    severity: TestCaseSeverity
    input: str
    expected_behavior: dict
    metadata: dict = {}
    is_active: bool

    class Config:
        from_attributes = True


class TestSuiteResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    version: int
    schema_version: str
    is_active: bool
    test_cases: List[TestCaseResponse] = []
    created_at: Union[datetime, str]
    updated_at: Union[datetime, str]

    class Config:
        from_attributes = True


class TestSuiteCreate(BaseModel):
    name: str
    description: Optional[str] = None
    test_cases: List[dict]


class ValidateResponse(BaseModel):
    valid: bool
    errors: List[str] = []


@router.get("/", response_model=List[TestSuiteResponse])
async def list_suites(
    skip: int = 0,
    limit: int = 100,
    suite_repo: TestSuiteRepository = Depends(get_suite_repo),
    case_repo: TestCaseRepository = Depends(get_case_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])),
):
    suites = await suite_repo.list(skip=skip, limit=limit, filters={"is_active": True})
    result = []
    for suite in suites:
        cases = await case_repo.list_by_suite(suite.id)
        result.append(TestSuiteResponse(
            id=suite.id,
            name=suite.name,
            description=suite.description,
            version=suite.version,
            schema_version=suite.schema_version,
            is_active=suite.is_active,
            created_at=suite.created_at,
            updated_at=suite.updated_at,
            test_cases=[_build_case_response(c) for c in cases],
        ))
    return result


@router.post("/", response_model=TestSuiteResponse, status_code=201)
async def create_suite(
    suite: TestSuiteCreate,
    suite_repo: TestSuiteRepository = Depends(get_suite_repo),
    case_repo: TestCaseRepository = Depends(get_case_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer"])),
):
    service = SuiteService(suite_repo, case_repo)
    created = await service.create_suite(suite.model_dump(), UUID(current_user.sub))
    cases = await case_repo.list_by_suite(created.id)
    return TestSuiteResponse(
        id=created.id, name=created.name, description=created.description,
        version=created.version, schema_version=created.schema_version, is_active=created.is_active,
        created_at=created.created_at, updated_at=created.updated_at,
        test_cases=[_build_case_response(c) for c in cases],
    )


@router.post("/validate", response_model=ValidateResponse)
async def validate_suite(
    suite: TestSuiteCreate,
    suite_repo: TestSuiteRepository = Depends(get_suite_repo),
    case_repo: TestCaseRepository = Depends(get_case_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer"])),
):
    service = SuiteService(suite_repo, case_repo)
    try:
        await service.validate_suite(suite.model_dump())
        return ValidateResponse(valid=True)
    except ValidationError as e:
        return ValidateResponse(valid=False, errors=[e.message])


@router.post("/import/yaml", response_model=TestSuiteResponse)
async def import_yaml(
    file: UploadFile = File(...),
    suite_repo: TestSuiteRepository = Depends(get_suite_repo),
    case_repo: TestCaseRepository = Depends(get_case_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer"])),
):
    content = await file.read()
    service = SuiteService(suite_repo, case_repo)
    created = await service.import_yaml(content.decode(), UUID(current_user.sub))
    cases = await case_repo.list_by_suite(created.id)
    return TestSuiteResponse(
        id=created.id, name=created.name, description=created.description,
        version=created.version, schema_version=created.schema_version, is_active=created.is_active,
        created_at=created.created_at, updated_at=created.updated_at,
        test_cases=[_build_case_response(c) for c in cases],
    )


@router.post("/import/json", response_model=TestSuiteResponse)
async def import_json(
    file: UploadFile = File(...),
    suite_repo: TestSuiteRepository = Depends(get_suite_repo),
    case_repo: TestCaseRepository = Depends(get_case_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer"])),
):
    content = await file.read()
    service = SuiteService(suite_repo, case_repo)
    created = await service.import_json(content.decode(), UUID(current_user.sub))
    cases = await case_repo.list_by_suite(created.id)
    return TestSuiteResponse(
        id=created.id, name=created.name, description=created.description,
        version=created.version, schema_version=created.schema_version, is_active=created.is_active,
        created_at=created.created_at, updated_at=created.updated_at,
        test_cases=[_build_case_response(c) for c in cases],
    )


@router.get("/{suite_id}", response_model=TestSuiteResponse)
async def get_suite(
    suite_id: UUID,
    suite_repo: TestSuiteRepository = Depends(get_suite_repo),
    case_repo: TestCaseRepository = Depends(get_case_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])),
):
    service = SuiteService(suite_repo, case_repo)
    suite = await service.get_suite_with_cases(suite_id)
    if not suite:
        raise NotFoundError("TestSuite", str(suite_id))
    cases = await case_repo.list_by_suite(suite.id)
    return TestSuiteResponse(
        id=suite.id, name=suite.name, description=suite.description,
        version=suite.version, schema_version=suite.schema_version, is_active=suite.is_active,
        created_at=suite.created_at, updated_at=suite.updated_at,
        test_cases=[_build_case_response(c) for c in cases],
    )


@router.post("/{suite_id}/versions", response_model=TestSuiteResponse)
async def create_version(
    suite_id: UUID,
    suite: TestSuiteCreate,
    changelog: str = "",
    suite_repo: TestSuiteRepository = Depends(get_suite_repo),
    case_repo: TestCaseRepository = Depends(get_case_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer"])),
):
    service = SuiteService(suite_repo, case_repo)
    updated = await service.create_version(suite_id, suite.model_dump(), UUID(current_user.sub), changelog)
    cases = await case_repo.list_by_suite(updated.id)
    return TestSuiteResponse(
        id=updated.id, name=updated.name, description=updated.description,
        version=updated.version, schema_version=updated.schema_version, is_active=updated.is_active,
        created_at=updated.created_at, updated_at=updated.updated_at,
        test_cases=[_build_case_response(c) for c in cases],
    )


@router.get("/{suite_id}/versions")
async def list_versions(
    suite_id: UUID,
    suite_repo: TestSuiteRepository = Depends(get_suite_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])),
):
    from app.repositories.suites import TestSuiteVersionRepository
    version_repo = TestSuiteVersionRepository(suite_repo.session)
    versions = await version_repo.list(filters={"suite_id": suite_id})
    return [{"version": v.version, "created_at": v.created_at.isoformat(), "changelog": v.changelog} for v in versions]
