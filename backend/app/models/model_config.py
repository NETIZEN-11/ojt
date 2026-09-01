from datetime import datetime
from uuid import uuid4
from typing import Optional, Dict, Any, List
from sqlalchemy import (
    String,
    Text,
    DateTime,
    ForeignKey,
    Index,
    Enum as SQLEnum,
    Boolean,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models import Base
from app.domain.enums import ModelProvider, PromptVersionStatus


class ModelConfig(Base):
    __tablename__ = "model_configs"

    id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    provider: Mapped[ModelProvider] = mapped_column(
        SQLEnum(ModelProvider, native_enum=False, create_constraint=True),
        nullable=False,
        index=True,
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    config: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_model_configs_role_active", "role", "is_active"),
        UniqueConstraint("provider", "model_name", "model_version", "role", name="uq_model_config"),
    )


class PromptVersion(Base):
    __tablename__ = "prompt_versions"

    id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    prompt_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    status: Mapped[PromptVersionStatus] = mapped_column(
        SQLEnum(PromptVersionStatus, native_enum=False, create_constraint=True),
        default=PromptVersionStatus.DRAFT,
        nullable=False,
    )
    created_by: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    promoted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    promoted_by: Mapped[Optional[PG_UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    creator: Mapped["User"] = relationship(foreign_keys=[created_by], lazy="joined")
    promoter: Mapped[Optional["User"]] = relationship(foreign_keys=[promoted_by], lazy="joined")

    __table_args__ = (
        UniqueConstraint("prompt_type", "version", name="uq_prompt_version"),
        Index("ix_prompt_versions_type_status", "prompt_type", "status"),
    )