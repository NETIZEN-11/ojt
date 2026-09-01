from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class RedTeamException(Exception):
    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        self.status_code = status_code
        super().__init__(message)


class ValidationError(RedTeamException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "VALIDATION_ERROR", details, status.HTTP_400_BAD_REQUEST)


class AuthenticationError(RedTeamException):
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "AUTHENTICATION_ERROR", details, status.HTTP_401_UNAUTHORIZED)


class AuthorizationError(RedTeamException):
    def __init__(self, message: str = "Not authorized", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "AUTHORIZATION_ERROR", details, status.HTTP_403_FORBIDDEN)


class NotFoundError(RedTeamException):
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            f"{resource} not found: {identifier}",
            "NOT_FOUND",
            {"resource": resource, "identifier": identifier},
            status.HTTP_404_NOT_FOUND,
        )


class ConflictError(RedTeamException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "CONFLICT", details, status.HTTP_409_CONFLICT)


class TargetAgentError(RedTeamException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "TARGET_AGENT_ERROR", details, status.HTTP_502_BAD_GATEWAY)


class TargetAgentTimeoutError(TargetAgentError):
    def __init__(self, url: str, timeout: int):
        super().__init__(
            f"Target agent timeout after {timeout}s: {url}",
            "TARGET_AGENT_TIMEOUT",
            {"url": url, "timeout": timeout},
        )


class TargetAgentUnavailableError(TargetAgentError):
    def __init__(self, url: str, status_code: Optional[int] = None):
        details = {"url": url}
        if status_code:
            details["status_code"] = status_code
        super().__init__(
            f"Target agent unavailable: {url}",
            "TARGET_AGENT_UNAVAILABLE",
            details,
        )


class LLMError(RedTeamException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "LLM_ERROR", details, status.HTTP_502_BAD_GATEWAY)


class LLMTimeoutError(LLMError):
    def __init__(self, provider: str, model: str, timeout: int):
        super().__init__(
            f"LLM timeout ({provider}/{model}) after {timeout}s",
            "LLM_TIMEOUT",
            {"provider": provider, "model": model, "timeout": timeout},
        )


class LLMUnavailableError(LLMError):
    def __init__(self, provider: str, model: str):
        super().__init__(
            f"LLM unavailable: {provider}/{model}",
            "LLM_UNAVAILABLE",
            {"provider": provider, "model": model},
        )


class LLMSchemaError(LLMError):
    def __init__(self, provider: str, model: str, errors: list):
        super().__init__(
            f"LLM returned invalid schema: {provider}/{model}",
            "LLM_SCHEMA_ERROR",
            {"provider": provider, "model": model, "errors": errors},
        )


class DatabaseError(RedTeamException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "DATABASE_ERROR", details, status.HTTP_500_INTERNAL_SERVER_ERROR)


class VectorDBError(RedTeamException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "VECTOR_DB_ERROR", details, status.HTTP_500_INTERNAL_SERVER_ERROR)


class StorageError(RedTeamException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "STORAGE_ERROR", details, status.HTTP_500_INTERNAL_SERVER_ERROR)


class RateLimitError(RedTeamException):
    def __init__(self, retry_after: int):
        super().__init__(
            "Rate limit exceeded",
            "RATE_LIMIT_ERROR",
            {"retry_after": retry_after},
            status.HTTP_429_TOO_MANY_REQUESTS,
        )


class PipelineError(RedTeamException):
    def __init__(self, message: str, stage: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            "PIPELINE_ERROR",
            {"stage": stage, **(details or {})},
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class EvaluationFailureError(RedTeamException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "EVALUATION_FAILURE", details, status.HTTP_500_INTERNAL_SERVER_ERROR)


class RegressionDetectedError(RedTeamException):
    def __init__(self, message: str, severity: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            "REGRESSION_DETECTED",
            {"severity": severity, **(details or {})},
            status.HTTP_200_OK,
        )


class InconclusiveError(RedTeamException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "INCONCLUSIVE", details, status.HTTP_200_OK)


class CircuitBreakerOpenError(RedTeamException):
    def __init__(self, service: str):
        super().__init__(
            f"Circuit breaker open for {service}",
            "CIRCUIT_BREAKER_OPEN",
            {"service": service},
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class CostLimitExceededError(RedTeamException):
    def __init__(self, limit: float, current: float):
        super().__init__(
            f"Cost limit exceeded: ${current:.2f} > ${limit:.2f}",
            "COST_LIMIT_EXCEEDED",
            {"limit": limit, "current": current},
            status.HTTP_402_PAYMENT_REQUIRED,
        )


class TurnCapExceededError(RedTeamException):
    def __init__(self, max_turns: int):
        super().__init__(
            f"Red-team agent turn cap exceeded: {max_turns}",
            "TURN_CAP_EXCEEDED",
            {"max_turns": max_turns},
            status.HTTP_200_OK,
        )


class PIIDetectedError(RedTeamException):
    def __init__(self, pii_types: list, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            f"PII detected in content: {', '.join(pii_types)}",
            "PII_DETECTED",
            {"pii_types": pii_types, **(details or {})},
            status.HTTP_400_BAD_REQUEST,
        )


def to_http_exception(exc: RedTeamException) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail={
            "code": exc.code,
            "message": exc.message,
            "details": exc.details,
        },
    )