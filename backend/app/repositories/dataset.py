from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.models.dataset import Dataset, DatasetVersion, DatasetSplit
from app.repositories.base import BaseRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class DatasetRepository(BaseRepository[Dataset]):
    def __init__(self, session: "AsyncSession"):
        super().__init__(session, Dataset)

    async def get_with_versions(self, dataset_id: UUID) -> Dataset | None:
        stmt = (
            select(Dataset)
            .where(Dataset.id == dataset_id)
            .options(selectinload(Dataset.versions).selectinload(DatasetVersion.dataset))
        )
        result = await self.session.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def get_active_by_name(self, name: str) -> Dataset | None:
        stmt = select(Dataset).where(Dataset.name == name, Dataset.status == "active")
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_status(
        self, status: str, skip: int = 0, limit: int = 100
    ) -> list[Dataset]:
        stmt = (
            select(Dataset)
            .where(Dataset.status == status)
            .order_by(Dataset.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_creator(
        self, created_by: UUID, skip: int = 0, limit: int = 100
    ) -> list[Dataset]:
        stmt = (
            select(Dataset)
            .where(Dataset.created_by == created_by)
            .order_by(Dataset.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class DatasetVersionRepository(BaseRepository[DatasetVersion]):
    def __init__(self, session: "AsyncSession"):
        super().__init__(session, DatasetVersion)

    async def get_latest(self, dataset_id: UUID) -> DatasetVersion | None:
        stmt = (
            select(DatasetVersion)
            .where(DatasetVersion.dataset_id == dataset_id)
            .order_by(DatasetVersion.version.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_version(self, dataset_id: UUID, version: int) -> DatasetVersion | None:
        stmt = select(DatasetVersion).where(
            DatasetVersion.dataset_id == dataset_id,
            DatasetVersion.version == version,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_dataset(
        self, dataset_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[DatasetVersion]:
        stmt = (
            select(DatasetVersion)
            .where(DatasetVersion.dataset_id == dataset_id)
            .order_by(DatasetVersion.version.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_next_version_number(self, dataset_id: UUID) -> int:
        stmt = select(func.max(DatasetVersion.version)).where(
            DatasetVersion.dataset_id == dataset_id
        )
        result = await self.session.execute(stmt)
        max_version = result.scalar_one_or_none()
        return (max_version or 0) + 1


class DatasetSplitRepository(BaseRepository[DatasetSplit]):
    def __init__(self, session: "AsyncSession"):
        super().__init__(session, DatasetSplit)

    async def get_by_version_and_name(
        self, dataset_version_id: UUID, split_name: str
    ) -> DatasetSplit | None:
        stmt = select(DatasetSplit).where(
            DatasetSplit.dataset_version_id == dataset_version_id,
            DatasetSplit.split_name == split_name,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_version(self, dataset_version_id: UUID) -> list[DatasetSplit]:
        stmt = select(DatasetSplit).where(
            DatasetSplit.dataset_version_id == dataset_version_id
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())