from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any
from uuid import UUID

from app.api.deps import get_db, require_role
from app.core.exceptions import NotFoundError
from app.core.security import TokenData
from app.repositories.base import BaseRepository
from app.guardrails import Guardrail, GuardrailFinding, GuardrailConfig, GuardrailType, GuardrailSeverity, GuardrailStatus

router = APIRouter()


class GuardrailCreate(BaseModel):
    name: str
    description: str | None = None
    guardrail_type: GuardrailType
    severity: GuardrailSeverity = GuardrailSeverity.MEDIUM
    pattern: str | None = None
    configuration: dict[str, Any] | None = None


class GuardrailUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    severity: GuardrailSeverity | None = None
    pattern: str | None = None
    status: GuardrailStatus | None = None
    configuration: dict[str, Any] | None = None


@router.get("/findings")
async def list_findings(
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "viewer"])),
):
    finding_repo = BaseRepository(GuardrailFinding, db)
    findings = await finding_repo.list()
    return findings


@router.get("/config")
async def list_guardrail_configs(db: AsyncSession = Depends(get_db)):
    config_repo = BaseRepository(GuardrailConfig, db)
    configs = await config_repo.list()
    return configs


@router.post("/config", status_code=201)
async def create_guardrail_config(
    config_data: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_role(["admin"])),
):
    config = GuardrailConfig(
        name=config_data.get("name", ""),
        guardrail_type=config_data.get("guardrail_type", GuardrailType.JAILBREAK),
        enabled=config_data.get("enabled", True),
        block_on_match=config_data.get("block_on_match", True),
        confidence_threshold=config_data.get("confidence_threshold", 0.8),
        configuration=config_data.get("configuration"),
    )
    config_repo = BaseRepository(GuardrailConfig, db)
    await config_repo.create(config)
    return config


@router.get("/")
async def list_guardrails(
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "viewer"])),
):
    guardrail_repo = BaseRepository(Guardrail, db)
    guardrails = await guardrail_repo.list()
    return guardrails


@router.post("/", status_code=201)
async def create_guardrail(
    guardrail_data: GuardrailCreate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer"])),
):
    guardrail = Guardrail(
        name=guardrail_data.name,
        description=guardrail_data.description,
        guardrail_type=guardrail_data.guardrail_type,
        severity=guardrail_data.severity,
        pattern=guardrail_data.pattern,
        configuration=guardrail_data.configuration,
    )
    guardrail_repo = BaseRepository(Guardrail, db)
    await guardrail_repo.create(guardrail)
    return guardrail


@router.get("/{guardrail_id}")
async def get_guardrail(
    guardrail_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "viewer"])),
):
    guardrail_repo = BaseRepository(Guardrail, db)
    guardrail = await guardrail_repo.get(guardrail_id)
    if not guardrail:
        raise NotFoundError("Guardrail", str(guardrail_id))
    return guardrail


@router.put("/{guardrail_id}")
async def update_guardrail(
    guardrail_id: UUID,
    guardrail_data: GuardrailUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer"])),
):
    guardrail_repo = BaseRepository(Guardrail, db)
    guardrail = await guardrail_repo.get(guardrail_id)
    if not guardrail:
        raise NotFoundError("Guardrail", str(guardrail_id))

    update_data = guardrail_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(guardrail, key, value)

    await db.add(guardrail)
    await db.commit()
    await db.refresh(guardrail)
    return guardrail


@router.delete("/{guardrail_id}", status_code=204)
async def delete_guardrail(
    guardrail_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_role(["admin"])),
):
    guardrail_repo = BaseRepository(Guardrail, db)
    guardrail = await guardrail_repo.get(guardrail_id)
    if not guardrail:
        raise NotFoundError("Guardrail", str(guardrail_id))
    await guardrail_repo.delete(guardrail_id)
    await db.commit()