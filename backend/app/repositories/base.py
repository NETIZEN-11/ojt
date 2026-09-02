from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

ModelType = TypeVar("ModelType", bound=DeclarativeBase)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get(self, id: UUID) -> ModelType | None:
        result = await self.session.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_by_field(self, field: str, value: Any) -> ModelType | None:
        result = await self.session.execute(
            select(self.model).where(getattr(self.model, field) == value)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: dict | None = None,
        order_by: str | None = None,
    ) -> list[ModelType]:
        query = select(self.model)
        if filters:
            for field, value in filters.items():
                query = query.where(getattr(self.model, field) == value)
        if order_by:
            query = query.order_by(getattr(self.model, order_by))
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count(self, filters: dict | None = None) -> int:
        query = select(func.count()).select_from(self.model)
        if filters:
            for field, value in filters.items():
                query = query.where(getattr(self.model, field) == value)
        result = await self.session.execute(query)
        return result.scalar_one()

    async def create(self, obj: ModelType) -> ModelType:
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def update(self, id: UUID, data: dict) -> ModelType | None:
        obj = await self.get(id)
        if not obj:
            return None
        for key, value in data.items():
            setattr(obj, key, value)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def delete(self, id: UUID) -> bool:
        obj = await self.get(id)
        if not obj:
            return False
        await self.session.delete(obj)
        await self.session.flush()
        return True

    async def exists(self, id: UUID) -> bool:
        result = await self.session.execute(
            select(func.count()).select_from(self.model).where(self.model.id == id)
        )
        return result.scalar_one() > 0
