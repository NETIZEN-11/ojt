from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import TokenData, get_regression_repo, require_role
from app.core.exceptions import NotFoundError
from app.domain.enums import RegressionType, SeverityLevel, Verdict
from app.repositories.baselines import RegressionRepository

router = APIRouter()


class RegressionResponse(BaseModel):
    id: UUID
    run_id: UUID
    baseline_id: UUID
    test_case_id: UUID
    previous_verdict: Verdict
    current_verdict: Verdict
    regression_type: RegressionType
    severity: SeverityLevel
    evidence: list[dict] = []
    acknowledged: bool = False
    created_at: datetime | str

    class Config:
        from_attributes = True


@router.get("/run/{run_id}", response_model=list[RegressionResponse])
async def list_regressions_by_run(
    run_id: UUID,
    severity: SeverityLevel | None = None,
    regression_repo: RegressionRepository = Depends(get_regression_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])),
):
    if severity:
        regressions = await regression_repo.list_by_severity(severity)
        regressions = [r for r in regressions if r.run_id == run_id]
    else:
        regressions = await regression_repo.list_by_run(run_id)
    return [RegressionResponse.model_validate(reg) for reg in regressions]


@router.get("/baseline/{baseline_id}", response_model=list[RegressionResponse])
async def list_regressions_by_baseline(
    baseline_id: UUID,
    regression_repo: RegressionRepository = Depends(get_regression_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])),
):
    regressions = await regression_repo.list_by_baseline(baseline_id)
    return [RegressionResponse.model_validate(reg) for reg in regressions]


@router.get("/{regression_id}", response_model=RegressionResponse)
async def get_regression(
    regression_id: UUID,
    regression_repo: RegressionRepository = Depends(get_regression_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])),
):
    regression = await regression_repo.get(regression_id)
    if not regression:
        raise NotFoundError("Regression", str(regression_id))
    return RegressionResponse.model_validate(regression)


@router.post("/{regression_id}/acknowledge")
async def acknowledge_regression(
    regression_id: UUID,
    regression_repo: RegressionRepository = Depends(get_regression_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer"])),
):
    regression = await regression_repo.get(regression_id)
    if not regression:
        raise NotFoundError("Regression", str(regression_id))

    regression.acknowledged = True
    regression.acknowledged_by = UUID(current_user.sub)
    regression.acknowledged_at = datetime.utcnow()
    await regression_repo.session.flush()

    return {"message": "Regression acknowledged"}
