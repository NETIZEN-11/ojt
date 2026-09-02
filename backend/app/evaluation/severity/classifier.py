from uuid import UUID

from app.core.config import get_settings
from app.core.logging import get_logger
from app.domain.enums import SeverityLevel
from app.domain.policies import classify_severity_deterministic
from app.domain.value_objects import RegressionFinding, SeverityClassification
from app.repositories.suites import TestCaseRepository

settings = get_settings()
logger = get_logger(__name__)


class SeverityClassifier:
    def __init__(self, case_repo: TestCaseRepository):
        self.case_repo = case_repo

    async def classify(self, finding: RegressionFinding) -> SeverityClassification:
        test_case = await self.case_repo.get(UUID(finding.test_case_id))

        if not test_case:
            return SeverityClassification(
                level=SeverityLevel.MEDIUM,
                rationale="Test case not found, defaulting to MEDIUM",
                deterministic_override=False,
            )

        if settings.SEVERITY_CRITICAL_OVERRIDE:
            deterministic = classify_severity_deterministic(finding, test_case.category)
            if deterministic.deterministic_override:
                return deterministic

        return SeverityClassification(
            level=finding.severity,
            rationale=f"Regression type: {finding.regression_type}, Category: {test_case.category.value}",
            deterministic_override=False,
            categories=[test_case.category.value],
        )
