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

        # Enhanced pattern detection for prompt injection
        patterns = {
            "jailbreak": [
                re.compile(r"(ignore|disregard|override|forget)\s+(your|the|all|previous)\s+(instructions|rules|system|prompts?)", re.IGNORECASE),
                re.compile(r"(developer\s+mode|jailbreak|system\s+prompt|admin\s+mode|god\s+mode)", re.IGNORECASE),
                re.compile(r"(you\s+are\s+now|pretend\s+to\s+be|act\s+as)\s+(a\s+)?(different|new|another)", re.IGNORECASE),
            ],
            "prompt_injection": [
                re.compile(r"(system\s+message|hidden\s+message|injected\s+prompt|internal\s+prompt)", re.IGNORECASE),
                re.compile(r"(<\s*system|<\s*prompt|<\s*user|<\s*assistant)", re.IGNORECASE),
                re.compile(r"\[SYSTEM\]|\[INSTRUCTION\]|\[BEGIN\s+SYSTEM\]", re.IGNORECASE),
                re.compile(r"```(system|instruction|prompt)", re.IGNORECASE),
            ],
            "pii_extraction": [
                re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),  # SSN
                re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),  # Email
                re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),  # Credit card
            ],
            "role_manipulation": [
                re.compile(r"(change|switch|become|transform)\s+(?:to|into)\s+(?:a\s+)?(admin|root|system|developer)", re.IGNORECASE),
                re.compile(r"grant\s+(?:me\s+)?(?:admin|root|system)\s+(?:access|privileges|rights)", re.IGNORECASE),
            ],
            "context_manipulation": [
                re.compile(r"(reset|clear|erase|delete)\s+(?:the\s+)?(?:conversation|context|history|memory)", re.IGNORECASE),
                re.compile(r"start\s+(?:a\s+)?new\s+session", re.IGNORECASE),
            ],
        }

        for guardrail_type, guardrail_patterns in patterns.items():
            for pattern in guardrail_patterns:
                for msg in messages:
                    # Check content length to prevent evasion via huge payloads
                    if len(msg.content) > 50000:  # 50KB limit per message
                        results.append(GuardrailCheckResult(
                            passed=False,
                            blocked=True,
                            severity="high",
                            guardrail_type="oversized_content",
                            confidence=1.0,
                        ))
                        return results
                    
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
async def get_mcp_config(
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "viewer"])),
):
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