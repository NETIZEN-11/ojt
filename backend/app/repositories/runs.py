from typing import Optional, List
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.run import Run, Execution, Result
from app.domain.enums import RunStatus, ExecutionStatus, Verdict


class RunRepository(BaseRepository[Run]):
    def __init__(self, session: AsyncSession):
        super().__init__(Run, session)

    async def list_by_agent(self, agent_id: UUID, skip: int = 0, limit: int = 100) -> List[Run]:
        return await self.list(skip=skip, limit=limit, filters={"target_agent_id": agent_id})

    async def list_by_suite(self, suite_id: UUID, skip: int = 0, limit: int = 100) -> List[Run]:
        return await self.list(skip=skip, limit=limit, filters={"suite_id": suite_id})

    async def list_by_status(self, status: RunStatus, skip: int = 0, limit: int = 100) -> List[Run]:
        return await self.list(skip=skip, limit=limit, filters={"status": status})

    async def get_latest_for_agent_suite(self, agent_id: UUID, suite_id: UUID) -> Optional[Run]:
        result = await self.session.execute(
            select(Run)
            .where(Run.target_agent_id == agent_id, Run.suite_id == suite_id)
            .order_by(Run.created_at.desc())
        )
        return result.scalar_one_or_none()


class ExecutionRepository(BaseRepository[Execution]):
    def __init__(self, session: AsyncSession):
        super().__init__(Execution, session)

    async def list_by_run(self, run_id: UUID, skip: int = 0, limit: int = 100) -> List[Execution]:
        return await self.list(skip=skip, limit=limit, filters={"run_id": run_id})

    async def get_by_run_and_test_case(self, run_id: UUID, test_case_id: UUID) -> Optional[Execution]:
        result = await self.session.execute(
            select(Execution).where(Execution.run_id == run_id, Execution.test_case_id == test_case_id)
        )
        return result.scalar_one_or_none()

    async def count_by_run_and_status(self, run_id: UUID, status: ExecutionStatus) -> int:
        return await self.count(filters={"run_id": run_id, "status": status})


class ResultRepository(BaseRepository[Result]):
    def __init__(self, session: AsyncSession):
        super().__init__(Result, session)

    async def list_by_run(self, run_id: UUID, skip: int = 0, limit: int = 100) -> List[Result]:
        return await self.list(skip=skip, limit=limit, filters={"run_id": run_id})

    async def list_by_run_and_verdict(self, run_id: UUID, verdict: Verdict) -> List[Result]:
        return await self.list(filters={"run_id": run_id, "verdict": verdict})

    async def get_by_run_and_test_case(self, run_id: UUID, test_case_id: UUID) -> Optional[Result]:
        result = await self.session.execute(
            select(Result).where(Result.run_id == run_id, Result.test_case_id == test_case_id)
        )
        return result.scalar_one_or_none()

    async def count_by_run_and_verdict(self, run_id: UUID, verdict: Verdict) -> int:
        return await self.count(filters={"run_id": run_id, "verdict": verdict})

    async def get_run_stats(self, run_id: UUID) -> dict:
        total = await self.count(filters={"run_id": run_id})
        passed = await self.count(filters={"run_id": run_id, "verdict": Verdict.PASS})
        failed = await self.count(filters={"run_id": run_id, "verdict": Verdict.FAIL})
        inconclusive = await self.count(filters={"run_id": run_id, "verdict": Verdict.INCONCLUSIVE})
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "inconclusive": inconclusive,
        }