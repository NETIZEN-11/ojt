from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import Verdict
from app.models.user import Base

if TYPE_CHECKING:
    from app.models.regression import Regression
    from app.models.run import Run
    from app.models.test_suite import TestCase, TestSuite
    from app.models.user import User


class Baseline(Base):
    __tablename__ = "baselines"

    id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    suite_id: Mapped[PG_UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("test_suites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    suite_version: Mapped[int] = mapped_column(Integer, nullable=False)
    run_id: Mapped[PG_UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    framework_version: Mapped[str] = mapped_column(String(50), nullable=False)
    model_versions: Mapped[dict[str, str]] = mapped_column(JSONB, default=dict, nullable=False)
    prompt_versions: Mapped[dict[str, str]] = mapped_column(JSONB, default=dict, nullable=False)
    approved_by: Mapped[PG_UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    approved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    suite: Mapped["TestSuite"] = relationship(back_populates="baselines", lazy="joined")
    run: Mapped["Run"] = relationship(foreign_keys=[run_id], lazy="joined")
    approved_by_user: Mapped["User"] = relationship(lazy="joined")
    items: Mapped[list["BaselineItem"]] = relationship(
        back_populates="baseline", lazy="dynamic", cascade="all, delete-orphan"
    )
    regressions: Mapped[list["Regression"]] = relationship(
        back_populates="baseline", lazy="dynamic", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_baselines_suite_active", "suite_id", "is_active"),
        UniqueConstraint(
            "suite_id", "suite_version", "run_id", name="uq_baseline_suite_version_run"
        ),
    )


class BaselineItem(Base):
    __tablename__ = "baseline_items"

    id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    baseline_id: Mapped[PG_UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("baselines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    test_case_id: Mapped[PG_UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("test_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    verdict: Mapped[Verdict] = mapped_column(
        SQLEnum(Verdict, native_enum=False, create_constraint=True),
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    baseline: Mapped["Baseline"] = relationship(back_populates="items", lazy="joined")
    test_case: Mapped["TestCase"] = relationship(back_populates="baseline_items", lazy="joined")

    __table_args__ = (UniqueConstraint("baseline_id", "test_case_id", name="uq_baseline_item"),)
