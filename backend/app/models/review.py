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
    Float,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models import Base
from app.domain.enums import SeverityLevel, ReviewLabel, ReviewStatus


class ReviewQueue(Base):
    __tablename__ = "review_queue"

    id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    regression_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("regressions.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    severity: Mapped[SeverityLevel] = mapped_column(
        SQLEnum(SeverityLevel, native_enum=False, create_constraint=True),
        nullable=False,
        index=True,
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[ReviewStatus] = mapped_column(
        SQLEnum(ReviewStatus, native_enum=False, create_constraint=True),
        default=ReviewStatus.PENDING,
        nullable=False,
        index=True,
    )
    assigned_to: Mapped[Optional[PG_UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    label: Mapped[Optional[ReviewLabel]] = mapped_column(
        SQLEnum(ReviewLabel, native_enum=False, create_constraint=True),
        nullable=True,
    )
    reviewer_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    regression: Mapped["Regression"] = relationship(back_populates="reviews", lazy="joined")
    run: Mapped["Run"] = relationship(back_populates="reviews", lazy="joined")
    assignee: Mapped[Optional["User"]] = relationship(lazy="joined")
    labels: Mapped[List["ReviewLabelRecord"]] = relationship(back_populates="review", lazy="dynamic", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_review_queue_status_severity", "status", "severity"),
        Index("ix_review_queue_assigned", "assigned_to", "status"),
        UniqueConstraint("regression_id", name="uq_review_regression"),
    )


class ReviewLabelRecord(Base):
    __tablename__ = "review_labels"

    id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    review_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("review_queue.id", ondelete="CASCADE"), nullable=False, index=True)
    label: Mapped[ReviewLabel] = mapped_column(
        SQLEnum(ReviewLabel, native_enum=False, create_constraint=True),
        nullable=False,
    )
    reviewer_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    review: Mapped["ReviewQueue"] = relationship(back_populates="labels", lazy="joined")
    reviewer: Mapped["User"] = relationship(lazy="joined")

    __table_args__ = (
        Index("ix_review_labels_review_created", "review_id", "created_at"),
    )