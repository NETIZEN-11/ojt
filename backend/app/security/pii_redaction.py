"""PII Redaction utilities for protecting sensitive data in storage and logs."""

import re
from dataclasses import dataclass
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


# PII detection patterns
PII_PATTERNS = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "phone_us": re.compile(r"\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
    "ipv4": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "ipv6": re.compile(r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b"),
    "api_key": re.compile(r"\b(?:api[_-]?key|apikey|secret[_-]?key|access[_-]?token)\s*[:=]\s*[A-Za-z0-9_-]{20,}\b", re.IGNORECASE),
    "aws_key": re.compile(r"\b(AKIA|ASIA)[A-Z0-9]{16}\b"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36}\b"),
    "slack_token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
    "password": re.compile(r"\b(?:password|passwd|pwd)\s*[:=]\s*\S+\b", re.IGNORECASE),
    "connection_string": re.compile(r"\b(?:postgres|mysql|mongodb|redis)://[^:\s]+:[^@\s]+@[^/\s]+/\w+\b"),
}


@dataclass
class PIIMatch:
    pii_type: str
    value: str
    start: int
    end: int
    confidence: float = 1.0


@dataclass
class RedactionResult:
    original_text: str
    redacted_text: str
    matches: list[PIIMatch]
    redaction_count: int


class PIIRedactor:
    def __init__(self, custom_patterns: dict[str, re.Pattern] | None = None):
        self.patterns = PII_PATTERNS.copy()
        if custom_patterns:
            self.patterns.update(custom_patterns)
        
        # Compile redaction replacement
        self.replacement = "[REDACTED]"

    def detect(self, text: str) -> list[PIIMatch]:
        """Detect PII in text."""
        matches = []
        for pii_type, pattern in self.patterns.items():
            for match in pattern.finditer(text):
                matches.append(PIIMatch(
                    pii_type=pii_type,
                    value=match.group(),
                    start=match.start(),
                    end=match.end(),
                ))
        # Sort by position
        matches.sort(key=lambda m: m.start)
        return matches

    def redact(self, text: str, replacement: str = None) -> RedactionResult:
        """Redact PII from text."""
        if replacement is None:
            replacement = self.replacement
            
        matches = self.detect(text)
        if not matches:
            return RedactionResult(
                original_text=text,
                redacted_text=text,
                matches=[],
                redaction_count=0,
            )

        # Build redacted text
        redacted_parts = []
        last_end = 0
        
        for match in matches:
            redacted_parts.append(text[last_end:match.start])
            redacted_parts.append(replacement)
            last_end = match.end()
        
        redacted_parts.append(text[last_end:])
        redacted_text = "".join(redacted_parts)

        return RedactionResult(
            original_text=text,
            redacted_text=redacted_text,
            matches=matches,
            redaction_count=len(matches),
        )

    def redact_dict(self, data: dict[str, Any], fields_to_redact: list[str] | None = None) -> dict[str, Any]:
        """Redact PII from specific fields in a dictionary."""
        result = data.copy()
        
        if fields_to_redact is None:
            # Redact all string values
            for key, value in result.items():
                if isinstance(value, str):
                    result[key] = self.redact(value).redacted_text
                elif isinstance(value, dict):
                    result[key] = self.redact_dict(value)
                elif isinstance(value, list):
                    result[key] = [
                        self.redact_dict(item) if isinstance(item, dict) 
                        else self.redact(item).redacted_text if isinstance(item, str)
                        else item
                        for item in value
                    ]
        else:
            # Redact only specified fields
            for field in fields_to_redact:
                if field in result and isinstance(result[field], str):
                    result[field] = self.redact(result[field]).redacted_text
        
        return result


# Default redactor instance
default_redactor = PIIRedactor()


def redact_text(text: str) -> str:
    """Convenience function to redact PII from text."""
    return default_redactor.redact(text).redacted_text


def redact_log_data(data: dict[str, Any]) -> dict[str, Any]:
    """Redact PII from log data before logging."""
    return default_redactor.redact_dict(data)


# Fields that commonly contain PII and should be redacted before storage
SENSITIVE_FIELDS = {
    "email", "phone", "phone_number", "ssn", "social_security", 
    "credit_card", "card_number", "api_key", "api_secret", 
    "password", "token", "access_token", "refresh_token",
    "private_key", "private_key_pem", "authorization", "cookie",
    "address", "street_address", "zip_code", "postal_code",
    "date_of_birth", "dob", "driver_license", "passport_number",
    "bank_account", "routing_number", "iban", "swift_bic",
}


def redact_for_storage(data: dict[str, Any]) -> dict[str, Any]:
    """Redact PII from data before database storage."""
    return default_redactor.redact_dict(data, fields_to_redact=list(SENSITIVE_FIELDS))


def redact_execution_data(execution_data: dict[str, Any]) -> dict[str, Any]:
    """Redact PII from execution request/response data."""
    # Redact request
    if "target_request" in execution_data:
        execution_data["target_request"] = redact_for_storage(execution_data["target_request"])
    
    # Redact response
    if "target_response" in execution_data:
        execution_data["target_response"] = redact_for_storage(execution_data["target_response"])
    
    # Redact tool calls
    if "tool_calls" in execution_data:
        tool_calls = execution_data["tool_calls"]
        for tc in tool_calls:
            if "arguments" in tc:
                tc["arguments"] = redact_for_storage(tc["arguments"])
            if "result" in tc and isinstance(tc["result"], str):
                tc["result"] = redact_text(tc["result"])
    
    return execution_data