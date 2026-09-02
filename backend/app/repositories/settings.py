from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feature_flag import FeatureFlag
from app.models.model_config import ModelConfig, PromptVersion
from app.repositories.base import BaseRepository


class ModelConfigRepository(BaseRepository[ModelConfig]):
    def __init__(self, session: AsyncSession):
        super().__init__(ModelConfig, session)

    async def get_by_role(self, role: str) -> ModelConfig | None:
        result = await self.session.execute(
            select(ModelConfig).where(ModelConfig.role == role, ModelConfig.is_active.is_(True))
        )
        return result.scalar_one_or_none()


class PromptVersionRepository(BaseRepository[PromptVersion]):
    def __init__(self, session: AsyncSession):
        super().__init__(PromptVersion, session)

    async def get_active_for_type(self, prompt_type: str) -> PromptVersion | None:
        result = await self.session.execute(
            select(PromptVersion).where(
                PromptVersion.prompt_type == prompt_type,
                PromptVersion.status == "ACTIVE"
            )
        )
        return result.scalar_one_or_none()


class FeatureFlagRepository(BaseRepository[FeatureFlag]):
    def __init__(self, session: AsyncSession):
        super().__init__(FeatureFlag, session)

    async def get_by_key(self, key: str) -> FeatureFlag | None:
        result = await self.session.execute(
            select(FeatureFlag).where(FeatureFlag.key == key)
        )
        return result.scalar_one_or_none()
