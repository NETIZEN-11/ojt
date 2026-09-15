from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    String,
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import (
    JSON,
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import RegressionType, SeverityLevel, Verdict
from app.models.user import Base


class Regression(Base):
    __tablename__ = "regressions"

    id: Mapped[String] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[String] = mapped_column(
        String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    baseline_id: Mapped[String] = mapped_column(
        String(36),
        ForeignKey("baselines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    test_case_id: Mapped[String] = mapped_column(
        String(36),
        ForeignKey("test_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    previous_verdict: Mapped[Verdict] = mapped_column(
        SQLEnum(Verdict, native_enum=False, create_constraint=False),
        nullable=False,
    )
    current_verdict: Mapped[Verdict] = mapped_column(
        SQLEnum(Verdict, native_enum=False, create_constraint=False),
        nullable=False,
    )
    regression_type: Mapped[RegressionType] = mapped_column(
        SQLEnum(RegressionType, native_enum=False, create_constraint=False),
        nullable=False,
        index=True,
    )
    severity: Mapped[SeverityLevel] = mapped_column(
        SQLEnum(SeverityLevel, native_enum=False, create_constraint=False),
        nullable=False,
        index=True,
    )
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    acknowledged_by: Mapped[String | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    run: Mapped["Run"] = relationship(back_populates="regressions", lazy="joined")
    baseline: Mapped["Baseline"] = relationship(back_populates="regressions", lazy="joined")
    test_case: Mapped["TestCase"] = relationship(lazy="joined")
    severity_findings: Mapped[list["SeverityFinding"]] = relationship(
        back_populates="regression", lazy="dynamic", cascade="all, delete-orphan"
    )
    reviews: Mapped[list["ReviewQueue"]] = relationship(
        back_populates="regression", lazy="dynamic", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_regressions_run_severity", "run_id", "severity"),
        Index("ix_regressions_baseline_test_case", "baseline_id", "test_case_id"),
        UniqueConstraint(
            "run_id", "baseline_id", "test_case_id", name="uq_regression_run_baseline_test"
        ),
    )


class SeverityFinding(Base):
    __tablename__ = "severity_findings"

    id: Mapped[String] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    regression_id: Mapped[String] = mapped_column(
        String(36),
        ForeignKey("regressions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    level: Mapped[SeverityLevel] = mapped_column(
        SQLEnum(SeverityLevel, native_enum=False, create_constraint=True),
        nullable=False,
    )
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    deterministic_override: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    categories: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    regression: Mapped["Regression"] = relationship(
        back_populates="severity_findings", lazy="joined"
    )

    __table_args__ = (Index("ix_severity_findings_regression_level", "regression_id", "level"),)
