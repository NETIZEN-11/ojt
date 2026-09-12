from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.models.user import Base


class CostEntryModel(Base):
    __tablename__ = "cost_entries"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id = Column(PG_UUID(as_uuid=True), ForeignKey("runs.id"), nullable=True, index=True)
    test_case_id = Column(PG_UUID(as_uuid=True), ForeignKey("test_cases.id"), nullable=True, index=True)
    category = Column(String(50), nullable=False, index=True)
    provider = Column(String(100), nullable=False, index=True)
    model = Column(String(100), nullable=False, index=True)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    currency = Column(String(3), default="USD")
    metadata_json = Column("metadata_json", JSON, default={}, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_cost_entries_run_category", "run_id", "category"),
        Index("ix_cost_entries_provider_model", "provider", "model"),
        Index("ix_cost_entries_created_at", "created_at"),
    )


class CostSummaryModel(Base):
    __tablename__ = "cost_summaries"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    period_start = Column(DateTime(timezone=True), nullable=False, index=True)
    period_end = Column(DateTime(timezone=True), nullable=False, index=True)
    total_cost_usd = Column(Float, default=0.0)
    total_input_tokens = Column(Integer, default=0)
    total_output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    by_category = Column(JSON, default={}, nullable=False)
    by_provider = Column(JSON, default={}, nullable=False)
    by_model = Column(JSON, default={}, nullable=False)
    by_run = Column(JSON, default={}, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_cost_summaries_period", "period_start", "period_end"),
    )


class CostTrendModel(Base):
    __tablename__ = "cost_trends"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    cost_usd = Column(Float, default=0.0)
    token_count = Column(Integer, default=0)
    request_count = Column(Integer, default=0)
    run_id = Column(PG_UUID(as_uuid=True), ForeignKey("runs.id"), nullable=True, index=True)
    provider = Column(String(100), nullable=True, index=True)
    model = Column(String(100), nullable=True, index=True)
    category = Column(String(50), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_cost_trends_date_run", "date", "run_id"),
        Index("ix_cost_trends_date_provider", "date", "provider"),
    )