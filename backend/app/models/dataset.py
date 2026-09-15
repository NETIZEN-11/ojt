from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional
from uuid import uuid4

from sqlalchemy import (
    JSON,
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
from sqlalchemy import JSON, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import TestCaseCategory
from app.models.user import Base

if TYPE_CHECKING:
    from app.models.test_suite import TestSuite


class DatasetStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[String] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[DatasetStatus] = mapped_column(
        SQLEnum(DatasetStatus, native_enum=False, create_constraint=True),
        default=DatasetStatus.DRAFT,
        nullable=False,
        index=True,
    )
    
    # Dataset configuration
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # file, database, api, synthetic
    source_config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    schema: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)  # column definitions
    
    # Splitting
    split_config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)  # train/val/test ratios
    split_seed: Mapped[int] = mapped_column(Integer, default=42)
    
    # Metadata
    total_records: Mapped[int] = mapped_column(Integer, default=0)
    total_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)  # SHA256
    
    # Versioning
    current_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    created_by: Mapped[String | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    versions: Mapped[list["DatasetVersion"]] = relationship(
        back_populates="dataset", lazy="dynamic", cascade="all, delete-orphan"
    )
    test_suites: Mapped[list["TestSuite"]] = relationship(back_populates="dataset", lazy="dynamic", foreign_keys="TestSuite.dataset_id")

    __table_args__ = (
        Index("ix_datasets_status_created", "status", "created_at"),
        Index("ix_datasets_name_status", "name", "status"),
    )


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"

    id: Mapped[String] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    dataset_id: Mapped[String] = mapped_column(
        String(36),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Snapshot
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)  # Full dataset snapshot
    changelog: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Split info
    split_sizes: Mapped[dict[str, int]] = mapped_column(JSON, default=dict, nullable=False)  # train/val/test counts
    
    # Metadata
    total_records: Mapped[int] = mapped_column(Integer, default=0)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by: Mapped[String | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    dataset: Mapped["Dataset"] = relationship(back_populates="versions", lazy="joined")

    __table_args__ = (
        UniqueConstraint("dataset_id", "version", name="uq_dataset_version"),
        Index("ix_dataset_versions_dataset_created", "dataset_id", "created_at"),
    )


class DatasetSplit(Base):
    __tablename__ = "dataset_splits"

    id: Mapped[String] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    dataset_version_id: Mapped[String] = mapped_column(
        String(36),
        ForeignKey("dataset_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    split_name: Mapped[str] = mapped_column(String(50), nullable=False)  # train, val, test
    
    # Split data reference
    records: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    record_indices: Mapped[list[int]] = mapped_column(JSON, default=list, nullable=False)  # Original dataset indices
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("dataset_version_id", "split_name", name="uq_dataset_split"),
    )