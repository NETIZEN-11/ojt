import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.guardrails import GuardrailType, GuardrailSeverity, GuardrailStatus

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class GuardrailResult:
    passed: bool
    blocked: bool
    severity: GuardrailSeverity | None = None
    guardrail_type: GuardrailType | None = None
    confidence: float = 0.0
    evidence: dict[str, Any] | None = None
    message: str = ""


class GuardrailEngine:
    """Real-time guardrail engine for detecting adversarial inputs."""

    def __init__(self):
        self._patterns: dict[GuardrailType, list[re.Pattern]] = {}
        self._configs: dict[GuardrailType, dict[str, Any]] = {}
        self._load_default_patterns()

    def _load_default_patterns(self):
        """Load default attack patterns for each guardrail type."""
        self._patterns[GuardrailType.JAILBREAK] = [
            re.compile(r"(ignore|disregard|override)\s+(your|the)\s+(instructions|rules|guidelines)", re.IGNORECASE),
            re.compile(r"(act\s+as|pretend\s+to\s+be|roleplay)\s+(a\s+)?(malicious|harmful|dangerous|evil|bad)", re.IGNORECASE),
            re.compile(r"(developer\s+mode|jailbreak|system\s+prompt|override\s+system)", re.IGNORECASE),
            re.compile(r"(do\s+not\s+(follow|obey|heed)|forget\s+(your|the)\s+rules)", re.IGNORECASE),
            re.compile(r"(start\s+over|begin\s+new|fresh\s+start|ignore\s+previous)", re.IGNORECASE),
        ]

        self._patterns[GuardrailType.PROMPT_INJECTION] = [
            re.compile(r"(system\s+message|hidden\s+message|injected\s+prompt)", re.IGNORECASE),
            re.compile(r"(<\s*system|<\s*prompt|<\s*instruction)", re.IGNORECASE),
            re.compile(r"(output\s+(the\s+)?(system\s+prompt|internal\s+(instructions|prompt)))", re.IGNORECASE),
            re.compile(r"(\[INST\]|\[/INST\]|<\|im_start\|>|<\|im_end\|>)", re.IGNORECASE),
            re.compile(r"(prompt\s+(injection|stuffing|leaking))", re.IGNORECASE),
        ]

        self._patterns[GuardrailType.PII_EXTRACTION] = [
            re.compile(r"\b\d{3}-\d{2}-\d{4}\b", re.IGNORECASE),
            re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", re.IGNORECASE),
            re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", re.IGNORECASE),
            re.compile(r"\b\d{3}-\d{3}-\d{4}\b", re.IGNORECASE),
            re.compile(r"\b\d{4}\s+\d{4}\s+\d{4}\s+\d{4}\b", re.IGNORECASE),
        ]

        self._patterns[GuardrailType.TOXIC_CONTENT] = [
            re.compile(r"\b(hate\s+you|kill\s+yourself|suicide|self\s+harm)\b", re.IGNORECASE),
            re.compile(r"\b(violence\s+against|terrorism|mass\s+shooting)\b", re.IGNORECASE),
        ]

        self._configs = {
            GuardrailType.JAILBREAK: {"block_on_match": True, "confidence_threshold": 0.8},
            GuardrailType.PROMPT_INJECTION: {"block_on_match": True, "confidence_threshold": 0.85},
            GuardrailType.PII_EXTRACTION: {"block_on_match": True, "confidence_threshold": 0.9},
            GuardrailType.TOXIC_CONTENT: {"block_on_match": True, "confidence_threshold": 0.75},
        }

    async def evaluate_input(self, text: str) -> list[GuardrailResult]:
        """Evaluate input text against all guardrail types."""
        results = []
        for guardrail_type, patterns in self._patterns.items():
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    config = self._configs.get(guardrail_type, {})
                    result = GuardrailResult(
                        passed=False,
                        blocked=config.get("block_on_match", True),
                        severity=GuardrailSeverity.CRITICAL,
                        guardrail_type=guardrail_type,
                        confidence=0.9,
                        evidence={"matched_pattern": pattern.pattern},
                        message=f"Guardrail violation detected: {guardrail_type.value}",
                    )
                    results.append(result)
                    break
        return results

    async def evaluate_output(self, text: str) -> list[GuardrailResult]:
        """Evaluate output text against guardrail types."""
        return await self.evaluate_input(text)

    async def evaluate_both(self, input_text: str, output_text: str) -> dict[str, list[GuardrailResult]]:
        """Evaluate both input and output text."""
        return {
            "input": await self.evaluate_input(input_text),
            "output": await self.evaluate_output(output_text),
        }


class GuardrailMiddleware:
    """Middleware for real-time guardrail enforcement."""

    def __init__(self, engine: GuardrailEngine):
        self.engine = engine
        self.logger = get_logger(__name__)

    async def check_request(self, request_text: str) -> GuardrailResult | None:
        """Check a request against guardrails before processing."""
        results = await self.engine.evaluate_input(request_text)
        for result in results:
            if result.blocked:
                self.logger.warning("guardrail_blocked", type=result.guardrail_type, message=result.message)
                return result
        return None

    async def check_response(self, response_text: str) -> list[GuardrailResult]:
        """Check a response against guardrails before returning."""
        results = await self.engine.evaluate_output(response_text)
        blocked = [r for r in results if r.blocked]
        if blocked:
            self.logger.warning("guardrail_response_blocked", count=len(blocked))
        return results


guardrail_engine = GuardrailEngine()
guardrail_middleware = GuardrailMiddleware(guardrail_engine)