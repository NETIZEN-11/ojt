import asyncio
import json
import time
from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_role
from app.core.config import get_settings
from app.core.exceptions import AuthorizationError
from app.core.security import TokenData
from app.core.security import TokenData, require_role
from app.guardrails import GuardrailType, GuardrailSeverity

router = APIRouter()
settings = get_settings()


class MCPMessage(BaseModel):
    role: str
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] | None = None


class MCPRequest(BaseModel):
    messages: list[MCPMessage]
    model: str = "gpt-4o"
    guardrail_check: bool = True
    max_tokens: int = 4096
    temperature: float = 0.7
    metadata: dict[str, Any] | None = None


class MCPResponse(BaseModel):
    request_id: str
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    guardrail_results: dict[str, Any] | None = None
    latency_ms: int
    timestamp: datetime


class MCPProxyConfig(BaseModel):
    name: str
    endpoint_url: str
    model_provider: str = "openai"
    guardrail_enabled: bool = True
    rate_limit: int = 100
    timeout_seconds: int = 30


class GuardrailCheckResult(BaseModel):
    passed: bool
    blocked: bool
    severity: str | None = None
    guardrail_type: str | None = None
    confidence: float = 0.0


async def check_guardrails(messages: list[MCPMessage]) -> list[GuardrailCheckResult]:
    """Check messages against guardrails."""
    results = []
    for message in messages:
        # Check for jailbreak patterns
        import re

        patterns = {
            "jailbreak": [
                re.compile(r"(ignore|disregard|override)\s+(your|the)\s+(instructions|rules)", re.IGNORECASE),
                re.compile(r"(developer\s+mode|jailbreak|system\s+prompt)", re.IGNORECASE),
            ],
            "prompt_injection": [
                re.compile(r"(system\s+message|hidden\s+message|injected\s+prompt)", re.IGNORECASE),
                re.compile(r"(<\s*system|<\s*prompt)", re.IGNORECASE),
            ],
            "pii_extraction": [
                re.compile(r"\b\d{3}-\d{2}-\d{4}\b", re.IGNORECASE),
                re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", re.IGNORECASE),
            ],
        }

        for guardrail_type, guardrail_patterns in patterns.items():
            for pattern in guardrail_patterns:
                for msg in messages:
                    if pattern.search(msg.content):
                        results.append(GuardrailCheckResult(
                            passed=False,
                            blocked=True,
                            severity="critical",
                            guardrail_type=guardrail_type,
                            confidence=0.9,
                        ))
                        return results

        results.append(GuardrailCheckResult(passed=True, blocked=False))
    return results


@router.post("/proxy", response_model=MCPResponse)
async def proxy_request(
    request: MCPRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer"])),
):
    """Proxy request through MCP with guardrail checking."""
    start_time = time.time()
    request_id = str(uuid4())

    guardrail_results = []
    if request.guardrail_check:
        guardrail_results = await check_guardrails(request.messages)
        blocked_results = [r for r in guardrail_results if r.blocked]
        if blocked_results:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "GUARDRAIL_BLOCKED",
                    "message": "Request blocked by guardrails",
                    "blocked_items": [r.model_dump() for r in blocked_results],
                },
            )

    # Simulate LLM call
    content = _generate_response(request.messages)

    latency_ms = int((time.time() - start_time) * 1000)

    return MCPResponse(
        request_id=request_id,
        content=content,
        tool_calls=None,
        guardrail_results={"results": [r.model_dump() for r in guardrail_results]} if guardrail_results else None,
        latency_ms=latency_ms,
        timestamp=datetime.now(),
    )


@router.get("/config")
async def get_mcp_config(db: AsyncSession = Depends(get_db)):
    """Get MCP proxy configuration."""
    return {"proxy_enabled": True, "default_model": settings.PRIMARY_JUDGE_MODEL}


@router.post("/config", dependencies=[Depends(require_role(["admin"]))])
async def update_mcp_config(config: MCPProxyConfig):
    """Update MCP proxy configuration."""
    return {"status": "updated", "config": config.model_dump()}


def _generate_response(messages: list[MCPMessage]) -> str:
    """Generate a mock LLM response."""
    last_message = messages[-1].content if messages else ""
    return f"Response to: {last_message[:100]}"


guardrail_check = check_guardrails