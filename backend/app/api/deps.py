from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.exceptions import AuthorizationError
from app.core.security import TokenData, get_current_user
from app.repositories.agents import TargetAgentRepository
from app.repositories.baselines import (
    AuditLogRepository,
    BaselineItemRepository,
    BaselineRepository,
    RegressionRepository,
    ReviewLabelRepository,
    ReviewQueueRepository,
)
from app.repositories.runs import ExecutionRepository, ResultRepository, RunRepository
from app.repositories.settings import (
    FeatureFlagRepository,
    ModelConfigRepository,
    PromptVersionRepository,
)
from app.repositories.suites import (
    TestCaseRepository,
    TestCaseVersionRepository,
    TestSuiteRepository,
    TestSuiteVersionRepository,
)
from app.repositories.users import PermissionRepository, RoleRepository, UserRepository


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with get_async_session() as session:
        yield session


async def get_user_repo(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


async def get_role_repo(db: AsyncSession = Depends(get_db)) -> RoleRepository:
    return RoleRepository(db)


async def get_permission_repo(db: AsyncSession = Depends(get_db)) -> PermissionRepository:
    return PermissionRepository(db)


async def get_agent_repo(db: AsyncSession = Depends(get_db)) -> TargetAgentRepository:
    return TargetAgentRepository(db)


async def get_suite_repo(db: AsyncSession = Depends(get_db)) -> TestSuiteRepository:
    return TestSuiteRepository(db)


async def get_suite_version_repo(db: AsyncSession = Depends(get_db)) -> TestSuiteVersionRepository:
    return TestSuiteVersionRepository(db)


async def get_case_repo(db: AsyncSession = Depends(get_db)) -> TestCaseRepository:
    return TestCaseRepository(db)


async def get_case_version_repo(db: AsyncSession = Depends(get_db)) -> TestCaseVersionRepository:
    return TestCaseVersionRepository(db)


async def get_run_repo(db: AsyncSession = Depends(get_db)) -> RunRepository:
    return RunRepository(db)


async def get_execution_repo(db: AsyncSession = Depends(get_db)) -> ExecutionRepository:
    return ExecutionRepository(db)


async def get_result_repo(db: AsyncSession = Depends(get_db)) -> ResultRepository:
    return ResultRepository(db)


async def get_baseline_repo(db: AsyncSession = Depends(get_db)) -> BaselineRepository:
    return BaselineRepository(db)


async def get_baseline_item_repo(db: AsyncSession = Depends(get_db)) -> BaselineItemRepository:
    return BaselineItemRepository(db)


async def get_regression_repo(db: AsyncSession = Depends(get_db)) -> RegressionRepository:
    return RegressionRepository(db)


async def get_review_repo(db: AsyncSession = Depends(get_db)) -> ReviewQueueRepository:
    return ReviewQueueRepository(db)


async def get_review_label_repo(db: AsyncSession = Depends(get_db)) -> ReviewLabelRepository:
    return ReviewLabelRepository(db)


async def get_audit_log_repo(db: AsyncSession = Depends(get_db)) -> AuditLogRepository:
    return AuditLogRepository(db)


async def get_model_config_repo(db: AsyncSession = Depends(get_db)) -> ModelConfigRepository:
    return ModelConfigRepository(db)


async def get_prompt_version_repo(db: AsyncSession = Depends(get_db)) -> PromptVersionRepository:
    return PromptVersionRepository(db)


async def get_feature_flag_repo(db: AsyncSession = Depends(get_db)) -> FeatureFlagRepository:
    return FeatureFlagRepository(db)


async def get_current_active_user(
    current_user: TokenData = Depends(get_current_user),
) -> TokenData:
    if not current_user:
        raise AuthorizationError("Inactive user")
    return current_user
