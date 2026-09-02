from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import ReviewStatus, SeverityLevel
from app.models.audit_log import AuditLog
from app.models.baseline import Baseline, BaselineItem
from app.models.regression import Regression, SeverityFinding
from app.models.review import ReviewLabelRecord, ReviewQueue
from app.repositories.base import BaseRepository


class BaselineRepository(BaseRepository[Baseline]):
    def __init__(self, session: AsyncSession):
        super().__init__(Baseline, session)

    async def get_active_for_suite(self, suite_id: UUID) -> Baseline | None:
        result = await self.session.execute(
            select(Baseline).where(Baseline.suite_id == suite_id, Baseline.is_active == True)
        )
        return result.scalar_one_or_none()

    async def get_by_suite_version(self, suite_id: UUID, suite_version: int) -> Baseline | None:
        result = await self.session.execute(
            select(Baseline).where(
                Baseline.suite_id == suite_id, Baseline.suite_version == suite_version
            )
        )
        return result.scalar_one_or_none()

    async def list_by_suite(self, suite_id: UUID) -> list[Baseline]:
        return await self.list(filters={"suite_id": suite_id})


class BaselineItemRepository(BaseRepository[BaselineItem]):
    def __init__(self, session: AsyncSession):
        super().__init__(BaselineItem, session)

    async def list_by_baseline(self, baseline_id: UUID) -> list[BaselineItem]:
        return await self.list(filters={"baseline_id": baseline_id})

    async def get_by_baseline_and_test_case(
        self, baseline_id: UUID, test_case_id: UUID
    ) -> BaselineItem | None:
        result = await self.session.execute(
            select(BaselineItem).where(
                BaselineItem.baseline_id == baseline_id, BaselineItem.test_case_id == test_case_id
            )
        )
        return result.scalar_one_or_none()


class RegressionRepository(BaseRepository[Regression]):
    def __init__(self, session: AsyncSession):
        super().__init__(Regression, session)

    async def list_by_run(self, run_id: UUID) -> list[Regression]:
        return await self.list(filters={"run_id": run_id})

    async def list_by_baseline(self, baseline_id: UUID) -> list[Regression]:
        return await self.list(filters={"baseline_id": baseline_id})

    async def list_by_severity(self, severity: SeverityLevel) -> list[Regression]:
        return await self.list(filters={"severity": severity})

    async def get_by_run_and_test_case(self, run_id: UUID, test_case_id: UUID) -> Regression | None:
        result = await self.session.execute(
            select(Regression).where(
                Regression.run_id == run_id, Regression.test_case_id == test_case_id
            )
        )
        return result.scalar_one_or_none()


class SeverityFindingRepository(BaseRepository[SeverityFinding]):
    def __init__(self, session: AsyncSession):
        super().__init__(SeverityFinding, session)

    async def get_by_regression(self, regression_id: UUID) -> SeverityFinding | None:
        result = await self.session.execute(
            select(SeverityFinding).where(SeverityFinding.regression_id == regression_id)
        )
        return result.scalar_one_or_none()


class ReviewQueueRepository(BaseRepository[ReviewQueue]):
    def __init__(self, session: AsyncSession):
        super().__init__(ReviewQueue, session)

    async def list_pending(self, skip: int = 0, limit: int = 100) -> list[ReviewQueue]:
        return await self.list(skip=skip, limit=limit, filters={"status": ReviewStatus.PENDING})

    async def list_by_status(
        self, status: ReviewStatus, skip: int = 0, limit: int = 100
    ) -> list[ReviewQueue]:
        return await self.list(skip=skip, limit=limit, filters={"status": status})

    async def list_by_assignee(
        self, assignee_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[ReviewQueue]:
        return await self.list(skip=skip, limit=limit, filters={"assigned_to": assignee_id})

    async def get_by_regression(self, regression_id: UUID) -> ReviewQueue | None:
        result = await self.session.execute(
            select(ReviewQueue).where(ReviewQueue.regression_id == regression_id)
        )
        return result.scalar_one_or_none()


class ReviewLabelRepository(BaseRepository[ReviewLabelRecord]):
    def __init__(self, session: AsyncSession):
        super().__init__(ReviewLabelRecord, session)

    async def list_by_review(self, review_id: UUID) -> list[ReviewLabelRecord]:
        return await self.list(filters={"review_id": review_id})

    async def get_latest_by_review(self, review_id: UUID) -> ReviewLabelRecord | None:
        result = await self.session.execute(
            select(ReviewLabelRecord)
            .where(ReviewLabelRecord.review_id == review_id)
            .order_by(ReviewLabelRecord.created_at.desc())
        )
        return result.scalar_one_or_none()


class AuditLogRepository(BaseRepository[AuditLog]):
    def __init__(self, session: AsyncSession):
        super().__init__(AuditLog, session)

    async def list_by_user(self, user_id: UUID, skip: int = 0, limit: int = 100) -> list[AuditLog]:
        return await self.list(skip=skip, limit=limit, filters={"user_id": user_id})

    async def list_by_resource(self, resource_type: str, resource_id: UUID) -> list[AuditLog]:
        return await self.list(filters={"resource_type": resource_type, "resource_id": resource_id})

    async def list_by_action(self, action: str, skip: int = 0, limit: int = 100) -> list[AuditLog]:
        return await self.list(skip=skip, limit=limit, filters={"action": action})
