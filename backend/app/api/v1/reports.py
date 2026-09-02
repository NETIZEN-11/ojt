from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import (
    TokenData,
    get_regression_repo,
    get_result_repo,
    get_review_repo,
    get_run_repo,
    require_role,
)
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.repositories.baselines import RegressionRepository, ReviewQueueRepository
from app.repositories.runs import ResultRepository, RunRepository

router = APIRouter()
logger = get_logger(__name__)


class RunReport(BaseModel):
    run_id: UUID
    timestamp: str
    suite_version: int
    baseline_version: str | None
    framework_version: str
    model_versions: dict
    prompt_versions: dict
    total_tests: int
    passed: int
    failed: int
    inconclusive: int
    regressions: int
    severity_breakdown: dict
    gate_decision: str
    total_cost_usd: float
    total_latency_ms: int
    review_items: int


@router.get("/run/{run_id}", response_model=RunReport)
async def get_run_report(
    run_id: UUID,
    run_repo: RunRepository = Depends(get_run_repo),
    result_repo: ResultRepository = Depends(get_result_repo),
    regression_repo: RegressionRepository = Depends(get_regression_repo),
    review_repo: ReviewQueueRepository = Depends(get_review_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])),
):
    run = await run_repo.get(run_id)
    if not run:
        raise NotFoundError("Run", str(run_id))

    regressions = await regression_repo.list_by_run(run_id)
    reviews = await review_repo.list_pending()

    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for reg in regressions:
        severity_counts[reg.severity.value] += 1

    gate_decision = "PASS"
    if run.critical_count > 0 or run.high_count > 0:
        gate_decision = "BLOCK"
    elif run.medium_count > 0 or run.low_count > 0:
        gate_decision = "WARN"
    elif run.inconclusive_count > 0:
        gate_decision = "FAIL"

    return RunReport(
        run_id=run.id,
        timestamp=run.created_at.isoformat(),
        suite_version=run.suite_version,
        baseline_version=str(run.baseline_id) if run.baseline_id else None,
        framework_version=run.framework_version,
        model_versions=run.model_versions,
        prompt_versions=run.prompt_versions,
        total_tests=run.total_tests,
        passed=run.passed_count,
        failed=run.failed_count,
        inconclusive=run.inconclusive_count,
        regressions=run.regression_count,
        severity_breakdown=severity_counts,
        gate_decision=gate_decision,
        total_cost_usd=run.total_cost_usd,
        total_latency_ms=run.total_latency_ms,
        review_items=len(reviews),
    )


@router.get("/run/{run_id}/markdown")
async def get_run_report_markdown(
    run_id: UUID,
    run_repo: RunRepository = Depends(get_run_repo),
    result_repo: ResultRepository = Depends(get_result_repo),
    regression_repo: RegressionRepository = Depends(get_regression_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])),
):
    report = await get_run_report(run_id, run_repo, result_repo, regression_repo, current_user)

    md = f"""# Run Report: {report.run_id}

**Timestamp:** {report.timestamp}
**Suite Version:** {report.suite_version}
**Baseline:** {report.baseline_version or 'N/A'}
**Framework Version:** {report.framework_version}

## Summary
- **Total Tests:** {report.total_tests}
- **Passed:** {report.passed}
- **Failed:** {report.failed}
- **Inconclusive:** {report.inconclusive}
- **Regressions:** {report.regressions}
- **Gate Decision:** {report.gate_decision}
- **Total Cost:** ${report.total_cost_usd:.4f}
- **Total Latency:** {report.total_latency_ms}ms

## Severity Breakdown
- **Critical:** {report.severity_breakdown['critical']}
- **High:** {report.severity_breakdown['high']}
- **Medium:** {report.severity_breakdown['medium']}
- **Low:** {report.severity_breakdown['low']}

## Model Versions
```json
{report.model_versions}
```

## Prompt Versions
```json
{report.prompt_versions}
```
"""
    return {"markdown": md}
