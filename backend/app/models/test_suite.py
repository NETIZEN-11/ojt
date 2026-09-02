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
    UniqueConstraint,
    func,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import ExpectedBehaviorType, TestCaseCategory, TestCaseSeverity
from app.models.user import Base

if TYPE_CHECKING:
    from app.models.baseline import Baseline, BaselineItem
    from app.models.run import Execution, Result, Run


class TestSuite(Base):
    __tablename__ = "test_suites"

    id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(20), default="1.0", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    created_by: Mapped[PG_UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    test_cases: Mapped[list["TestCase"]] = relationship(
        back_populates="suite", lazy="dynamic", cascade="all, delete-orphan"
    )
    versions: Mapped[list["TestSuiteVersion"]] = relationship(
        back_populates="suite", lazy="dynamic", cascade="all, delete-orphan"
    )
    runs: Mapped[list["Run"]] = relationship(back_populates="suite", lazy="dynamic")
    baselines: Mapped[list["Baseline"]] = relationship(back_populates="suite", lazy="dynamic")

    __table_args__ = (
        Index("ix_test_suites_name_version", "name", "version"),
        UniqueConstraint("name", "version", name="uq_test_suite_name_version"),
    )


class TestSuiteVersion(Base):
    __tablename__ = "test_suite_versions"

    id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    suite_id: Mapped[PG_UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("test_suites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    changelog: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by: Mapped[PG_UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    suite: Mapped["TestSuite"] = relationship(back_populates="versions", lazy="joined")

    __table_args__ = (UniqueConstraint("suite_id", "version", name="uq_test_suite_version"),)


class TestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    suite_id: Mapped[PG_UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("test_suites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    test_case_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    category: Mapped[TestCaseCategory] = mapped_column(
        SQLEnum(TestCaseCategory, native_enum=False, create_constraint=True),
        nullable=False,
        index=True,
    )
    severity: Mapped[TestCaseSeverity] = mapped_column(
        SQLEnum(TestCaseSeverity, native_enum=False, create_constraint=True),
        nullable=False,
    )
    input: Mapped[str] = mapped_column(Text, nullable=False)
    expected_behavior_type: Mapped[ExpectedBehaviorType] = mapped_column(
        SQLEnum(ExpectedBehaviorType, native_enum=False, create_constraint=True),
        nullable=False,
    )
    matcher_config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    rubric_config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    test_case_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    created_by: Mapped[PG_UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    suite: Mapped["TestSuite"] = relationship(back_populates="test_cases", lazy="joined")
    versions: Mapped[list["TestCaseVersion"]] = relationship(
        back_populates="test_case", lazy="dynamic", cascade="all, delete-orphan"
    )
    executions: Mapped[list["Execution"]] = relationship(back_populates="test_case", lazy="dynamic")
    results: Mapped[list["Result"]] = relationship(back_populates="test_case", lazy="dynamic")
    baseline_items: Mapped[list["BaselineItem"]] = relationship(
        back_populates="test_case", lazy="dynamic"
    )

    __table_args__ = (
        UniqueConstraint(
            "suite_id", "test_case_id", "version", name="uq_test_case_suite_id_version"
        ),
        Index("ix_test_cases_suite_category", "suite_id", "category"),
    )


class TestCaseVersion(Base):
    __tablename__ = "test_case_versions"

    id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    test_case_id: Mapped[PG_UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("test_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    changelog: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by: Mapped[PG_UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    test_case: Mapped["TestCase"] = relationship(back_populates="versions", lazy="joined")

    __table_args__ = (UniqueConstraint("test_case_id", "version", name="uq_test_case_version"),)
