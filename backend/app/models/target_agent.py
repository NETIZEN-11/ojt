from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import AgentStatus
from app.models.user import Base

if TYPE_CHECKING:
    from app.models.run import Run


class TargetAgent(Base):
    __tablename__ = "target_agents"

    id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    endpoint_url: Mapped[str] = mapped_column(String(500), nullable=False)
    auth_config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    request_template: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    response_extraction: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    allowed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[AgentStatus] = mapped_column(
        SQLEnum(AgentStatus, native_enum=False, create_constraint=True),
        default=AgentStatus.ACTIVE,
        nullable=False,
    )
    health_check_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    last_health_check: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by: Mapped[PG_UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    runs: Mapped[list["Run"]] = relationship(back_populates="target_agent", lazy="dynamic")

    __table_args__ = (
        Index("ix_target_agents_status_allowed", "status", "allowed"),
    )
