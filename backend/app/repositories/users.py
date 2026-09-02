from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import Permission, Role, User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        result = await self.session.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_with_roles(self, id: UUID) -> User | None:
        result = await self.session.execute(
            select(User)
            .options(selectinload(User.roles).selectinload(Role.permissions))
            .where(User.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_email_or_username(self, identifier: str) -> User | None:
        result = await self.session.execute(
            select(User).where(or_(User.email == identifier, User.username == identifier))
        )
        return result.scalar_one_or_none()

    async def list_active(self, skip: int = 0, limit: int = 100) -> list[User]:
        return await self.list(skip=skip, limit=limit, filters={"is_active": True})


class RoleRepository(BaseRepository[Role]):
    def __init__(self, session: AsyncSession):
        super().__init__(Role, session)

    async def get_by_name(self, name: str) -> Role | None:
        result = await self.session.execute(select(Role).where(Role.name == name))
        return result.scalar_one_or_none()

    async def get_with_permissions(self, id: UUID) -> Role | None:
        result = await self.session.execute(
            select(Role).options(selectinload(Role.permissions)).where(Role.id == id)
        )
        return result.scalar_one_or_none()


class PermissionRepository(BaseRepository[Permission]):
    def __init__(self, session: AsyncSession):
        super().__init__(Permission, session)

    async def get_by_name(self, name: str) -> Permission | None:
        result = await self.session.execute(select(Permission).where(Permission.name == name))
        return result.scalar_one_or_none()

    async def get_by_resource_action(self, resource: str, action: str) -> Permission | None:
        result = await self.session.execute(
            select(Permission).where(Permission.resource == resource, Permission.action == action)
        )
        return result.scalar_one_or_none()
