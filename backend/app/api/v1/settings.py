from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import datetime
from typing import List, Optional, Union
from pydantic import BaseModel

from app.api.deps import get_db, get_model_config_repo, get_prompt_version_repo, get_feature_flag_repo, get_current_active_user, require_role, TokenData
from app.repositories import ModelConfigRepository, PromptVersionRepository, FeatureFlagRepository
from app.models.model_config import ModelConfig, PromptVersion
from app.models.feature_flag import FeatureFlag
from app.domain.enums import ModelProvider, PromptVersionStatus
from app.core.exceptions import NotFoundError
from app.core.config import get_settings

router = APIRouter()
settings = get_settings()


class ModelConfigResponse(BaseModel):
    id: UUID
    provider: ModelProvider
    model_name: str
    model_version: str
    role: str
    config: dict
    is_active: bool
    is_default: bool

    class Config:
        from_attributes = True


class ModelConfigCreate(BaseModel):
    provider: ModelProvider
    model_name: str
    model_version: str
    role: str
    config: dict = {}
    is_default: bool = False


class PromptVersionResponse(BaseModel):
    id: UUID
    prompt_type: str
    version: str
    content: str
    variables: List[str]
    status: PromptVersionStatus
    created_by: UUID
    created_at: Union[datetime, str]
    promoted_at: Optional[Union[datetime, str]] = None
    promoted_by: Optional[UUID]

    class Config:
        from_attributes = True


class PromotePromptRequest(BaseModel):
    prompt_type: str
    version: str


class FeatureFlagResponse(BaseModel):
    id: UUID
    name: str
    enabled: bool
    description: str
    rollout_percentage: int
    metadata: dict

    class Config:
        from_attributes = True


class FeatureFlagUpdate(BaseModel):
    enabled: Optional[bool] = None
    rollout_percentage: Optional[int] = None


@router.get("/models", response_model=List[ModelConfigResponse])
async def list_models(
    model_repo: ModelConfigRepository = Depends(get_model_config_repo),
    current_user: TokenData = Depends(require_role(["admin"])),
):
    models = await model_repo.list()
    return [ModelConfigResponse.model_validate(m) for m in models]


@router.post("/models", response_model=ModelConfigResponse)
async def create_model(
    model: ModelConfigCreate,
    model_repo: ModelConfigRepository = Depends(get_model_config_repo),
    current_user: TokenData = Depends(require_role(["admin"])),
):
    new_model = ModelConfig(**model.model_dump())
    new_model = await model_repo.create(new_model)
    return ModelConfigResponse.model_validate(new_model)


@router.get("/prompts", response_model=List[PromptVersionResponse])
async def list_prompts(
    prompt_repo: PromptVersionRepository = Depends(get_prompt_version_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer"])),
):
    prompts = await prompt_repo.list()
    return [PromptVersionResponse.model_validate(p) for p in prompts]


@router.post("/prompts/promote")
async def promote_prompt(
    request: PromotePromptRequest,
    prompt_repo: PromptVersionRepository = Depends(get_prompt_version_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer"])),
):
    prompt = await prompt_repo.get_by_type_version(request.prompt_type, request.version)
    if not prompt:
        raise NotFoundError("PromptVersion", f"{request.prompt_type}/{request.version}")

    await prompt_repo.demote_all(request.prompt_type)
    prompt.status = PromptVersionStatus.ACTIVE
    prompt.promoted_at = datetime.utcnow()
    prompt.promoted_by = UUID(current_user.sub)
    await prompt_repo.session.flush()

    return {"message": "Prompt promoted"}


@router.get("/feature-flags", response_model=List[FeatureFlagResponse])
async def list_feature_flags(
    flag_repo: FeatureFlagRepository = Depends(get_feature_flag_repo),
    current_user: TokenData = Depends(require_role(["admin"])),
):
    flags = await flag_repo.list()
    return [FeatureFlagResponse.model_validate(f) for f in flags]


@router.patch("/feature-flags/{flag_id}")
async def update_feature_flag(
    flag_id: UUID,
    update: FeatureFlagUpdate,
    flag_repo: FeatureFlagRepository = Depends(get_feature_flag_repo),
    current_user: TokenData = Depends(require_role(["admin"])),
):
    flag = await flag_repo.get(flag_id)
    if not flag:
        raise NotFoundError("FeatureFlag", str(flag_id))

    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(flag, key, value)

    await flag_repo.session.flush()
    return {"message": "Feature flag updated"}


@router.get("/config")
async def get_config(
    current_user: TokenData = Depends(require_role(["admin"])),
):
    return {
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "eval_mode": settings.EVAL_MODE,
        "judge_model": settings.PRIMARY_JUDGE_MODEL,
        "generator_model": settings.GENERATOR_MODEL,
        "planner_model": settings.PLANNER_MODEL,
        "embedding_model": settings.EMBEDDING_MODEL,
        "cost_per_run_limit": settings.COST_PER_RUN_LIMIT_USD,
        "cost_daily_limit": settings.COST_DAILY_LIMIT_USD,
        "retention_days": {
            "transcripts": settings.TRANSCRIPT_RETENTION_DAYS,
            "critical_findings": settings.CRITICAL_FINDINGS_RETENTION_DAYS,
            "reports": settings.REPORT_RETENTION_DAYS,
            "audit_logs": settings.AUDIT_LOG_RETENTION_DAYS,
        },
    }