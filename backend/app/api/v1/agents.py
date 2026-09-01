from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import datetime
from typing import List, Optional, Union
from pydantic import BaseModel, HttpUrl

from app.api.deps import get_db, get_agent_repo, get_current_active_user, require_role, TokenData
from app.repositories.agents import TargetAgentRepository
from app.models.target_agent import TargetAgent
from app.domain.enums import AgentStatus
from app.core.exceptions import NotFoundError, ConflictError
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


class TargetAgentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    endpoint_url: HttpUrl
    auth_config: dict = {}
    request_template: dict = {}
    response_extraction: dict = {}
    timeout_seconds: int = 30
    max_retries: int = 3
    health_check_url: Optional[HttpUrl] = None


class TargetAgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    endpoint_url: Optional[HttpUrl] = None
    auth_config: Optional[dict] = None
    request_template: Optional[dict] = None
    response_extraction: Optional[dict] = None
    timeout_seconds: Optional[int] = None
    max_retries: Optional[int] = None
    allowed: Optional[bool] = None
    health_check_url: Optional[HttpUrl] = None


class TargetAgentResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    endpoint_url: str
    auth_config: dict
    request_template: dict
    response_extraction: dict
    timeout_seconds: int
    max_retries: int
    allowed: bool
    status: AgentStatus
    health_check_url: Optional[str] = None
    created_at: Union[datetime, str]
    updated_at: Union[datetime, str]

    class Config:
        from_attributes = True


class HealthCheckResponse(BaseModel):
    healthy: bool
    latency_ms: Optional[int] = None
    error: Optional[str] = None


@router.get("/", response_model=List[TargetAgentResponse])
async def list_agents(
    skip: int = 0,
    limit: int = 100,
    agent_repo: TargetAgentRepository = Depends(get_agent_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])),
):
    agents = await agent_repo.list(skip=skip, limit=limit)
    return [TargetAgentResponse.model_validate(agent) for agent in agents]


@router.post("/", response_model=TargetAgentResponse, status_code=201)
async def create_agent(
    agent: TargetAgentCreate,
    agent_repo: TargetAgentRepository = Depends(get_agent_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer"])),
):
    existing = await agent_repo.get_by_name(agent.name)
    if existing:
        raise ConflictError(f"Agent with name '{agent.name}' already exists")

    new_agent = TargetAgent(
        **agent.model_dump(),
        created_by=UUID(current_user.sub),
    )
    new_agent = await agent_repo.create(new_agent)
    return TargetAgentResponse.model_validate(new_agent)


@router.get("/{agent_id}", response_model=TargetAgentResponse)
async def get_agent(
    agent_id: UUID,
    agent_repo: TargetAgentRepository = Depends(get_agent_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])),
):
    agent = await agent_repo.get(agent_id)
    if not agent:
        raise NotFoundError("TargetAgent", str(agent_id))
    return TargetAgentResponse.model_validate(agent)


@router.patch("/{agent_id}", response_model=TargetAgentResponse)
async def update_agent(
    agent_id: UUID,
    update: TargetAgentUpdate,
    agent_repo: TargetAgentRepository = Depends(get_agent_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer"])),
):
    agent = await agent_repo.get(agent_id)
    if not agent:
        raise NotFoundError("TargetAgent", str(agent_id))

    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(agent, key, value)

    await agent_repo.session.flush()
    return TargetAgentResponse.model_validate(agent)


@router.post("/{agent_id}/test", response_model=HealthCheckResponse)
async def test_agent(
    agent_id: UUID,
    agent_repo: TargetAgentRepository = Depends(get_agent_repo),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer"])),
):
    agent = await agent_repo.get(agent_id)
    if not agent:
        raise NotFoundError("TargetAgent", str(agent_id))

    from app.providers.target_agent import TargetAgentProviderFactory
    provider = TargetAgentProviderFactory.create_provider(
        "http",
        endpoint_url=agent.endpoint_url,
        auth_config=agent.auth_config,
        request_template=agent.request_template,
        response_extraction=agent.response_extraction,
        timeout=agent.timeout_seconds,
        max_retries=agent.max_retries,
    )

    try:
        import time
        start = time.time()
        healthy = await provider.health_check()
        latency = int((time.time() - start) * 1000)
        return HealthCheckResponse(healthy=healthy, latency_ms=latency)
    except Exception as e:
        return HealthCheckResponse(healthy=False, error=str(e))


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: UUID,
    agent_repo: TargetAgentRepository = Depends(get_agent_repo),
    current_user: TokenData = Depends(require_role(["admin"])),
):
    deleted = await agent_repo.delete(agent_id)
    if not deleted:
        raise NotFoundError("TargetAgent", str(agent_id))
    return {"message": "Agent deleted"}