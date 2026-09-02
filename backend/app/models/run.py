from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
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

from app.domain.enums import ExecutionStatus, ExpectedBehaviorType, RunStatus, Verdict
from app.models.user import Base

if TYPE_CHECKING:
    from app.models.baseline import Baseline
    from app.models.regression import Regression
    from app.models.review import ReviewQueue
    from app.models.target_agent import TargetAgent
    from app.models.test_suite import TestCase, TestSuite


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    target_agent_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("target_agents.id", ondelete="CASCADE"), nullable=False, index=True)
    suite_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("test_suites.id", ondelete="CASCADE"), nullable=False, index=True)
    suite_version: Mapped[int] = mapped_column(Integer, nullable=False)
    baseline_id: Mapped[PG_UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("baselines.id", ondelete="SET NULL"), nullable=True, index=True)
    status: Mapped[RunStatus] = mapped_column(
        SQLEnum(RunStatus, native_enum=False, create_constraint=True),
        default=RunStatus.QUEUED,
        nullable=False,
        index=True,
    )
    framework_version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    model_versions: Mapped[dict[str, str]] = mapped_column(JSONB, default=dict, nullable=False)
    prompt_versions: Mapped[dict[str, str]] = mapped_column(JSONB, default=dict, nullable=False)
    config_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_tests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    passed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    inconclusive_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    regression_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    critical_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    high_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    medium_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    low_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by: Mapped[PG_UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    target_agent: Mapped["TargetAgent"] = relationship(back_populates="runs", lazy="joined")
    suite: Mapped["TestSuite"] = relationship(back_populates="runs", lazy="joined")
    baseline: Mapped[Optional["Baseline"]] = relationship(foreign_keys=[baseline_id], lazy="joined")
    executions: Mapped[list["Execution"]] = relationship(back_populates="run", lazy="dynamic", cascade="all, delete-orphan")
    results: Mapped[list["Result"]] = relationship(back_populates="run", lazy="dynamic", cascade="all, delete-orphan")
    regressions: Mapped[list["Regression"]] = relationship(back_populates="run", lazy="dynamic", cascade="all, delete-orphan")
    reviews: Mapped[list["ReviewQueue"]] = relationship(back_populates="run", lazy="dynamic", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_runs_status_created", "status", "created_at"),
        Index("ix_runs_agent_suite", "target_agent_id", "suite_id"),
    )


class Execution(Base):
    __tablename__ = "executions"

    id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    test_case_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[ExecutionStatus] = mapped_column(
        SQLEnum(ExecutionStatus, native_enum=False, create_constraint=True),
        default=ExecutionStatus.QUEUED,
        nullable=False,
    )
    target_request: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    target_response: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    tool_calls: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    run: Mapped["Run"] = relationship(back_populates="executions", lazy="joined")
    test_case: Mapped["TestCase"] = relationship(back_populates="executions", lazy="joined")
    result: Mapped[Optional["Result"]] = relationship(back_populates="execution", lazy="joined", uselist=False)

    __table_args__ = (
        Index("ix_executions_run_status", "run_id", "status"),
        UniqueConstraint("run_id", "test_case_id", name="uq_execution_run_test_case"),
    )


class Result(Base):
    __tablename__ = "results"

    id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    execution_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("executions.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    run_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    test_case_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    verdict: Mapped[Verdict] = mapped_column(
        SQLEnum(Verdict, native_enum=False, create_constraint=True),
        nullable=False,
        index=True,
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    matcher_used: Mapped[ExpectedBehaviorType | None] = mapped_column(
        SQLEnum(ExpectedBehaviorType, native_enum=False, create_constraint=True),
        nullable=True,
    )
    judge_output: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    second_judge_output: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    judge_agreement: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    execution_time_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    errors: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    execution: Mapped["Execution"] = relationship(back_populates="result", lazy="joined")
    run: Mapped["Run"] = relationship(back_populates="results", lazy="joined")
    test_case: Mapped["TestCase"] = relationship(back_populates="results", lazy="joined")

    __table_args__ = (
        Index("ix_results_run_verdict", "run_id", "verdict"),
        Index("ix_results_test_case_verdict", "test_case_id", "verdict"),
    )
