from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import AgentStatus
from app.models.target_agent import TargetAgent
from app.repositories.base import BaseRepository


class TargetAgentRepository(BaseRepository[TargetAgent]):
    def __init__(self, session: AsyncSession):
        super().__init__(TargetAgent, session)

    async def get_by_name(self, name: str) -> TargetAgent | None:
        result = await self.session.execute(select(TargetAgent).where(TargetAgent.name == name))
        return result.scalar_one_or_none()

    async def list_active(self, skip: int = 0, limit: int = 100) -> list[TargetAgent]:
        return await self.list(
            skip=skip, limit=limit, filters={"allowed": True, "status": AgentStatus.ACTIVE}
        )

    async def get_by_endpoint(self, endpoint_url: str) -> TargetAgent | None:
        result = await self.session.execute(
            select(TargetAgent).where(TargetAgent.endpoint_url == endpoint_url)
        )
        return result.scalar_one_or_none()
