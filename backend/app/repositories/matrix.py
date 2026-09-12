from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.matrix import EvaluationMatrix, EvaluationMatrixCell
from app.repositories.base import BaseRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class EvaluationMatrixRepository(BaseRepository[EvaluationMatrix]):
    def __init__(self, session: "AsyncSession"):
        super().__init__(session, EvaluationMatrix)

    async def get_with_cells(self, matrix_id: UUID) -> EvaluationMatrix | None:
        stmt = (
            select(EvaluationMatrix)
            .where(EvaluationMatrix.id == matrix_id)
            .options(selectinload(EvaluationMatrix.cells).selectinload(EvaluationMatrixCell.test_case))
        )
        result = await self.session.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def get_with_runs(self, matrix_id: UUID) -> EvaluationMatrix | None:
        stmt = (
            select(EvaluationMatrix)
            .where(EvaluationMatrix.id == matrix_id)
            .options(selectinload(EvaluationMatrix.runs))
        )
        result = await self.session.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def list_by_suite(
        self, suite_id: UUID, skip: int = 0, limit: int = 100, status: str | None = None
    ) -> list[EvaluationMatrix]:
        stmt = select(EvaluationMatrix).where(EvaluationMatrix.suite_id == suite_id)
        if status:
            stmt = stmt.where(EvaluationMatrix.status == status)
        stmt = stmt.order_by(EvaluationMatrix.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_active_by_suite(self, suite_id: UUID) -> list[EvaluationMatrix]:
        stmt = (
            select(EvaluationMatrix)
            .where(
                EvaluationMatrix.suite_id == suite_id,
                EvaluationMatrix.status.in_(["QUEUED", "VALIDATING", "RUNNING", "SCORING", "DIFFING", "CLASSIFYING", "GATING", "REVIEW_REQUIRED"]),
            )
            .order_by(EvaluationMatrix.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class EvaluationMatrixCellRepository(BaseRepository[EvaluationMatrixCell]):
    def __init__(self, session: "AsyncSession"):
        super().__init__(session, EvaluationMatrixCell)

    async def get_by_matrix_and_test_case(
        self, matrix_id: UUID, test_case_id: UUID
    ) -> EvaluationMatrixCell | None:
        stmt = select(EvaluationMatrixCell).where(
            EvaluationMatrixCell.matrix_id == matrix_id,
            EvaluationMatrixCell.test_case_id == test_case_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_matrix(
        self, matrix_id: UUID, status: str | None = None
    ) -> list[EvaluationMatrixCell]:
        stmt = select(EvaluationMatrixCell).where(EvaluationMatrixCell.matrix_id == matrix_id)
        if status:
            stmt = stmt.where(EvaluationMatrixCell.status == status)
        stmt = stmt.order_by(EvaluationMatrixCell.created_at)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_pending_by_matrix(self, matrix_id: UUID) -> list[EvaluationMatrixCell]:
        stmt = select(EvaluationMatrixCell).where(
            EvaluationMatrixCell.matrix_id == matrix_id,
            EvaluationMatrixCell.status.in_(["QUEUED", "VALIDATING"]),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_running_by_matrix(self, matrix_id: UUID) -> list[EvaluationMatrixCell]:
        stmt = select(EvaluationMatrixCell).where(
            EvaluationMatrixCell.matrix_id == matrix_id,
            EvaluationMatrixCell.status == "RUNNING",
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self, cell_id: UUID, status: str, started_at: str | None = None, completed_at: str | None = None, error: str | None = None
    ) -> EvaluationMatrixCell | None:
        cell = await self.get(cell_id)
        if not cell:
            return None
        cell.status = status
        if started_at:
            cell.started_at = started_at
        if completed_at:
            cell.completed_at = completed_at
        if error:
            cell.error_message = error
        cell.updated_at = cell.updated_at  # trigger update
        await self.session.flush()
        return cell

    async def increment_matrix_counters(self, matrix_id: UUID, completed: int = 0, failed: int = 0):
        from app.models.matrix import EvaluationMatrix
        stmt = select(EvaluationMatrix).where(EvaluationMatrix.id == matrix_id)
        result = await self.session.execute(stmt)
        matrix = result.scalar_one_or_none()
        if matrix:
            matrix.completed_cells += completed
            matrix.failed_cells += failed
            matrix.updated_at = datetime.utcnow()
            await self.session.flush()