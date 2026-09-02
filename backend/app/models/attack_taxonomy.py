from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import TestCaseSeverity
from app.models.user import Base


class AttackTaxonomy(Base):
    __tablename__ = "attack_taxonomy"

    id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    subcategory: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    technique: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    examples: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, nullable=False)
    severity: Mapped[TestCaseSeverity] = mapped_column(
        SQLEnum(TestCaseSeverity, native_enum=False, create_constraint=True),
        nullable=False,
    )
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_attack_taxonomy_category_severity", "category", "severity"),
        UniqueConstraint("category", "subcategory", "technique", name="uq_attack_taxonomy"),
    )


class EmbeddingDocument(Base):
    __tablename__ = "embedding_documents"

    id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    collection: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    doc_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __init__(self, **kwargs):
        if "metadata" in kwargs:
            kwargs["doc_metadata"] = kwargs.pop("metadata")
        super().__init__(**kwargs)
