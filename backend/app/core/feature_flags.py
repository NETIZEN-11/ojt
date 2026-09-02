from typing import Any

from pydantic import BaseModel

from app.core.config import get_settings

settings = get_settings()


class FeatureFlag(BaseModel):
    name: str
    enabled: bool
    description: str
    rollout_percentage: int = 100
    metadata: dict[str, Any] = {}


FEATURE_FLAGS: dict[str, FeatureFlag] = {
    "adversarial_generator": FeatureFlag(
        name="adversarial_generator",
        enabled=settings.FEATURE_ADVERSARIAL_GENERATOR,
        description="Enable adversarial test case generation",
    ),
    "redteam_agent": FeatureFlag(
        name="redteam_agent",
        enabled=settings.FEATURE_REDTEAM_AGENT,
        description="Enable multi-turn red-team agent",
    ),
    "secondary_judge": FeatureFlag(
        name="secondary_judge",
        enabled=settings.FEATURE_SECONDARY_JUDGE,
        description="Enable double-scoring with secondary judge",
    ),
    "rag_retrieval": FeatureFlag(
        name="rag_retrieval",
        enabled=settings.FEATURE_RAG_RETRIEVAL,
        description="Enable RAG-based retrieval for context",
    ),
    "streaming_responses": FeatureFlag(
        name="streaming_responses",
        enabled=settings.FEATURE_STREAMING_RESPONSES,
        description="Enable streaming API responses",
    ),
    "experimental_ui": FeatureFlag(
        name="experimental_ui",
        enabled=settings.FEATURE_EXPERIMENTAL_UI,
        description="Enable experimental UI features",
    ),
}


class FeatureFlagService:
    def __init__(self):
        self._flags = FEATURE_FLAGS.copy()
        self._overrides: dict[str, bool] = {}

    def is_enabled(self, flag_name: str, user_id: str | None = None) -> bool:
        if flag_name in self._overrides:
            return self._overrides[flag_name]
        flag = self._flags.get(flag_name)
        if not flag:
            return False
        return flag.enabled

    def get_flag(self, flag_name: str) -> FeatureFlag | None:
        return self._flags.get(flag_name)

    def list_flags(self) -> dict[str, FeatureFlag]:
        return self._flags.copy()

    def set_override(self, flag_name: str, enabled: bool) -> None:
        self._overrides[flag_name] = enabled

    def clear_override(self, flag_name: str) -> None:
        self._overrides.pop(flag_name, None)

    def update_flag(self, flag_name: str, enabled: bool) -> bool:
        if flag_name in self._flags:
            self._flags[flag_name].enabled = enabled
            return True
        return False


feature_flag_service = FeatureFlagService()


def requires_feature(flag_name: str):
    def decorator(func):
        import functools

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if not feature_flag_service.is_enabled(flag_name):
                from app.core.exceptions import RedTeamException

                raise RedTeamException(
                    f"Feature '{flag_name}' is not enabled",
                    "FEATURE_DISABLED",
                    {"feature": flag_name},
                    404,
                )
            return await func(*args, **kwargs)

        return wrapper

    return decorator
