import sys
from datetime import UTC

import structlog
from structlog.types import EventDict, Processor

from app.core.config import get_settings

settings = get_settings()


def add_severity_level(logger: structlog.BoundLogger, method_name: str, event_dict: EventDict) -> EventDict:
    event_dict["level"] = method_name.upper()
    return event_dict


def add_timestamp(logger: structlog.BoundLogger, method_name: str, event_dict: EventDict) -> EventDict:
    from datetime import datetime
    event_dict["timestamp"] = datetime.now(UTC).isoformat()
    return event_dict


def add_service_info(logger: structlog.BoundLogger, method_name: str, event_dict: EventDict) -> EventDict:
    event_dict["service"] = settings.OTEL_SERVICE_NAME
    event_dict["environment"] = settings.ENVIRONMENT
    return event_dict


def filter_sensitive_data(logger: structlog.BoundLogger, method_name: str, event_dict: EventDict) -> EventDict:
    sensitive_keys = {
        "password", "secret", "token", "api_key", "apikey",
        "authorization", "cookie", "session", "private_key",
        "jwt", "bearer", "access_token", "refresh_token",
    }
    filtered = {}
    for key, value in event_dict.items():
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            filtered[key] = "***REDACTED***"
        elif isinstance(value, str) and len(value) > 1000:
            filtered[key] = value[:1000] + "... [truncated]"
        else:
            filtered[key] = value
    return filtered


def setup_logging() -> None:
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        add_severity_level,
        add_timestamp,
        add_service_info,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        filter_sensitive_data,
    ]

    if settings.LOG_FORMAT == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    import logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    )


def get_logger(name: str) -> structlog.BoundLogger:
    return structlog.get_logger(name)
