from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
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
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import RunStatus
from app.models.run import Run
from app.models.user import Base

if TYPE_CHECKING:
    from app.models.test_suite import TestCase, TestSuite


class EvaluationMatrix(Base):
    __tablename__ = "evaluation_matrices"

    id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    suite_id: Mapped[PG_UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("test_suites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    suite_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[RunStatus] = mapped_column(
        SQLEnum(RunStatus, native_enum=False, create_constraint=True),
        default=RunStatus.QUEUED,
        nullable=False,
        index=True,
    )
    test_case_ids: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    configurations: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    total_cells: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_cells: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_cells: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    created_by: Mapped[PG_UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    suite: Mapped["TestSuite"] = relationship(back_populates="matrices", lazy="joined")
    cells: Mapped[list["EvaluationMatrixCell"]] = relationship(
        back_populates="matrix", lazy="dynamic", cascade="all, delete-orphan"
    )
    runs: Mapped[list["Run"]] = relationship(back_populates="matrix", lazy="dynamic")

    __table_args__ = (
        Index("ix_matrices_suite_status", "suite_id", "status"),
        Index("ix_matrices_created", "created_at"),
    )


class EvaluationMatrixCell(Base):
    __tablename__ = "evaluation_matrix_cells"

    id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    matrix_id: Mapped[PG_UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("evaluation_matrices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    test_case_id: Mapped[PG_UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("test_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    configuration: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    run_id: Mapped[PG_UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[RunStatus] = mapped_column(
        SQLEnum(RunStatus, native_enum=False, create_constraint=True),
        default=RunStatus.QUEUED,
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    matrix: Mapped["EvaluationMatrix"] = relationship(back_populates="cells", lazy="joined")
    test_case: Mapped["TestCase"] = relationship(lazy="joined")
    run: Mapped[Optional["Run"]] = relationship(foreign_keys=[run_id], lazy="joined")

    __table_args__ = (
        Index("ix_matrix_cells_matrix_status", "matrix_id", "status"),
        Index("ix_matrix_cells_test_case", "test_case_id"),
        UniqueConstraint("matrix_id", "test_case_id", "run_id", name="uq_matrix_cell_unique"),
    )