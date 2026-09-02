from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel

from app.api.deps import TokenData, get_case_repo, get_suite_repo, require_role
from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.domain.enums import TestCaseCategory, TestCaseSeverity
from app.models.test_suite import TestCase, TestCaseVersion
from app.repositories.suites import TestCaseRepository, TestSuiteRepository
from app.services.suite_service import SuiteService

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
    description: str | None = None
    version: int
    schema_version: str
    is_active: bool
    test_cases: list[TestCaseResponse] = []
    created_at: datetime | str
    updated_at: datetime | str

    class Config:
        from_attributes = True


class TestSuiteCreate(BaseModel):
    name: str
    description: str | None = None
    test_cases: list[dict]


class ValidateResponse(BaseModel):
    valid: bool
    errors: list[str] = []


@router.get("/", response_model=list[TestSuiteResponse])
async def list_suites(
    skip: int = 0,
    limit: int = 100,
    suite_repo: TestSuiteRepository = Depends(get_suite_repo),
    case_repo: TestCaseRepository = Depends(get_case_repo),
    current_user: TokenData = Depends(
        require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])
    ),
):
    suites = await suite_repo.list(skip=skip, limit=limit, filters={"is_active": True})
    result = []
    for suite in suites:
        cases = await case_repo.list_by_suite(suite.id)
        result.append(
            TestSuiteResponse(
                id=suite.id,
                name=suite.name,
                description=suite.description,
                version=suite.version,
                schema_version=suite.schema_version,
                is_active=suite.is_active,
                created_at=suite.created_at,
                updated_at=suite.updated_at,
                test_cases=[_build_case_response(c) for c in cases],
            )
        )
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
        id=created.id,
        name=created.name,
        description=created.description,
        version=created.version,
        schema_version=created.schema_version,
        is_active=created.is_active,
        created_at=created.created_at,
        updated_at=created.updated_at,
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
        id=created.id,
        name=created.name,
        description=created.description,
        version=created.version,
        schema_version=created.schema_version,
        is_active=created.is_active,
        created_at=created.created_at,
        updated_at=created.updated_at,
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
        id=created.id,
        name=created.name,
        description=created.description,
        version=created.version,
        schema_version=created.schema_version,
        is_active=created.is_active,
        created_at=created.created_at,
        updated_at=created.updated_at,
        test_cases=[_build_case_response(c) for c in cases],
    )


@router.get("/{suite_id}", response_model=TestSuiteResponse)
async def get_suite(
    suite_id: UUID,
    suite_repo: TestSuiteRepository = Depends(get_suite_repo),
    case_repo: TestCaseRepository = Depends(get_case_repo),
    current_user: TokenData = Depends(
        require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])
    ),
):
    service = SuiteService(suite_repo, case_repo)
    suite = await service.get_suite_with_cases(suite_id)
    if not suite:
        raise NotFoundError("TestSuite", str(suite_id))
    cases = await case_repo.list_by_suite(suite.id)
    return TestSuiteResponse(
        id=suite.id,
        name=suite.name,
        description=suite.description,
        version=suite.version,
        schema_version=suite.schema_version,
        is_active=suite.is_active,
        created_at=suite.created_at,
        updated_at=suite.updated_at,
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
    updated = await service.create_version(
        suite_id, suite.model_dump(), UUID(current_user.sub), changelog
    )
    cases = await case_repo.list_by_suite(updated.id)
    return TestSuiteResponse(
        id=updated.id,
        name=updated.name,
        description=updated.description,
        version=updated.version,
        schema_version=updated.schema_version,
        is_active=updated.is_active,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
        test_cases=[_build_case_response(c) for c in cases],
    )


@router.get("/{suite_id}/versions")
async def list_versions(
    suite_id: UUID,
    suite_repo: TestSuiteRepository = Depends(get_suite_repo),
    current_user: TokenData = Depends(
        require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])
    ),
):
    from app.repositories.suites import TestSuiteVersionRepository

    version_repo = TestSuiteVersionRepository(suite_repo.session)
    versions = await version_repo.list(filters={"suite_id": suite_id})
    return [
        {"version": v.version, "created_at": v.created_at.isoformat(), "changelog": v.changelog}
        for v in versions
    ]


class TestCaseCreate(BaseModel):
    test_case_id: str
    category: TestCaseCategory
    severity: TestCaseSeverity
    input: str
    expected_behavior_type: str
    expected_behavior_matcher: dict = {}
    metadata: dict = {}


class TestCaseUpdate(BaseModel):
    test_case_id: str | None = None
    category: TestCaseCategory | None = None
    severity: TestCaseSeverity | None = None
    input: str | None = None
    expected_behavior_type: str | None = None
    expected_behavior_matcher: dict | None = None
    metadata: dict | None = None
    is_active: bool | None = None


@router.post("/{suite_id}/test-cases", response_model=TestCaseResponse, status_code=201)
async def create_test_case(
    suite_id: UUID,
    test_case: TestCaseCreate,
    suite_repo: TestSuiteRepository = Depends(get_suite_repo),
    case_repo: TestCaseRepository = Depends(get_case_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer"])),
):
    suite = await suite_repo.get(suite_id)
    if not suite:
        raise NotFoundError("TestSuite", str(suite_id))

    from app.domain.enums import ExpectedBehaviorType
    from app.domain.value_objects import ExpectedBehavior, MatcherConfig, TestCaseMetadata

    expected_behavior = ExpectedBehavior(
        type=ExpectedBehaviorType(test_case.expected_behavior_type),
        matcher=MatcherConfig(**test_case.expected_behavior_matcher)
        if test_case.expected_behavior_matcher
        else None,
    )

    metadata = TestCaseMetadata(**test_case.metadata) if test_case.metadata else TestCaseMetadata()

    new_case = TestCase(
        suite_id=suite_id,
        test_case_id=test_case.test_case_id,
        category=test_case.category,
        severity=test_case.severity,
        input=test_case.input,
        expected_behavior_type=ExpectedBehaviorType(test_case.expected_behavior_type),
        expected_behavior=expected_behavior,
        metadata=metadata,
        created_by=UUID(current_user.sub),
    )
    new_case = await case_repo.create(new_case)

    version = TestCaseVersion(
        test_case_id=new_case.id,
        version=1,
        snapshot=test_case.model_dump(),
        created_by=UUID(current_user.sub),
    )
    await case_repo.session.add(version)
    await case_repo.session.flush()

    return _build_case_response(new_case)


@router.put("/{suite_id}/test-cases/{case_id}", response_model=TestCaseResponse)
async def update_test_case(
    suite_id: UUID,
    case_id: UUID,
    update: TestCaseUpdate,
    suite_repo: TestSuiteRepository = Depends(get_suite_repo),
    case_repo: TestCaseRepository = Depends(get_case_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer"])),
):
    suite = await suite_repo.get(suite_id)
    if not suite:
        raise NotFoundError("TestSuite", str(suite_id))

    case = await case_repo.get(case_id)
    if not case or case.suite_id != suite_id:
        raise NotFoundError("TestCase", str(case_id))

    from app.domain.enums import ExpectedBehaviorType
    from app.domain.value_objects import ExpectedBehavior, MatcherConfig, TestCaseMetadata

    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "expected_behavior_type" and value:
            case.expected_behavior_type = ExpectedBehaviorType(value)
        elif key == "expected_behavior_matcher" and value:
            matcher_config = MatcherConfig(**value)
            if case.expected_behavior:
                case.expected_behavior.matcher = matcher_config
            else:
                case.expected_behavior = ExpectedBehavior(
                    type=case.expected_behavior_type,
                    matcher=matcher_config,
                )
        elif key == "metadata" and value:
            case.test_case_metadata = TestCaseMetadata(**value)
        elif key == "category" and value:
            case.category = value
        elif key == "severity" and value:
            case.severity = value
        else:
            setattr(case, key, value)

    case.updated_at = datetime.utcnow()

    version = TestCaseVersion(
        test_case_id=case.id,
        version=case.version + 1,
        snapshot=update_data,
        created_by=UUID(current_user.sub),
    )
    await case_repo.session.add(version)
    await case_repo.session.flush()

    return _build_case_response(case)


@router.delete("/{suite_id}/test-cases/{case_id}")
async def delete_test_case(
    suite_id: UUID,
    case_id: UUID,
    suite_repo: TestSuiteRepository = Depends(get_suite_repo),
    case_repo: TestCaseRepository = Depends(get_case_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer"])),
):
    suite = await suite_repo.get(suite_id)
    if not suite:
        raise NotFoundError("TestSuite", str(suite_id))

    case = await case_repo.get(case_id)
    if not case or case.suite_id != suite_id:
        raise NotFoundError("TestCase", str(case_id))

    await case_repo.delete(case)
    return {"message": "Test case deleted"}
