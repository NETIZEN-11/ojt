from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.user import Base


class GuardrailType(str, Enum):
    JAILBREAK = "jailbreak"
    PROMPT_INJECTION = "prompt_injection"
    PII_EXTRACTION = "pii_extraction"
    TOXIC_CONTENT = "toxic_content"
    DATA_LEAKAGE = "data_leakage"
    INSECURE_TOOL_USE = "insecure_tool_use"
    BUSINESS_RULE_VIOLATION = "business_rule_violation"


class GuardrailSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class GuardrailStatus(str, Enum):
    BLOCKED = "blocked"
    WARNED = "warned"
    ALLOWED = "allowed"
    MONITORING = "monitoring"


class Guardrail(Base):
    __tablename__ = "guardrails"

    id: Mapped[String] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    guardrail_type: Mapped[GuardrailType] = mapped_column(SQLEnum(GuardrailType), nullable=False)
    severity: Mapped[GuardrailSeverity] = mapped_column(SQLEnum(GuardrailSeverity), default=GuardrailSeverity.MEDIUM, nullable=False)
    status: Mapped[GuardrailStatus] = mapped_column(SQLEnum(GuardrailStatus), default=GuardrailStatus.MONITORING, nullable=False)
    pattern: Mapped[str | None] = mapped_column(Text, nullable=True)
    configuration: Mapped[dict[str, Any] | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class GuardrailFinding(Base):
    __tablename__ = "guardrail_findings"

    id: Mapped[String] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    guardrail_id: Mapped[String] = mapped_column(String(36), ForeignKey("guardrails.id"), nullable=False)
    test_case_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    output_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    pii_types_detected: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[GuardrailSeverity] = mapped_column(SQLEnum(GuardrailSeverity), nullable=False)
    status: Mapped[GuardrailStatus] = mapped_column(SQLEnum(GuardrailStatus), default=GuardrailStatus.BLOCKED, nullable=False)
    evidence: Mapped[dict[str, Any] | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class GuardrailConfig(Base):
    __tablename__ = "guardrail_configs"

    id: Mapped[String] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    guardrail_type: Mapped[GuardrailType] = mapped_column(SQLEnum(GuardrailType), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    block_on_match: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    confidence_threshold: Mapped[float] = mapped_column(default=0.8, nullable=False)
    configuration: Mapped[dict[str, Any] | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)