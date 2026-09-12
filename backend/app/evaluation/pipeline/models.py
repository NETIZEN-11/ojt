from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class PipelineStepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PipelineStatus(str, Enum):
    QUEUED = "queued"
    VALIDATING = "validating"
    BUILDING_MATRIX = "building_matrix"
    SCHEDULING = "scheduling"
    EXECUTING = "executing"
    AGGREGATING = "aggregating"
    COMPARING_BASELINE = "comparing_baseline"
    CLASSIFYING_SEVERITY = "classifying_severity"
    EVALUATING_GATE = "evaluating_gate"
    AWAITING_REVIEW = "awaiting_review"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PipelineStep(BaseModel):
    name: str
    status: PipelineStepStatus = PipelineStepStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PipelineConfig(BaseModel):
    """Configuration for an evaluation pipeline."""
    name: str
    description: Optional[str] = None
    
    # Dataset
    dataset_id: UUID
    dataset_version: Optional[int] = None
    
    # Test Suite
    suite_id: UUID
    suite_version: Optional[int] = None
    
    # Target Agent
    target_agent_id: UUID
    
    # Matrix Configuration (Test Case × Model × Prompt × Provider)
    models: list[dict[str, Any]] = Field(default_factory=list)  # model_id, provider, parameters
    prompt_versions: list[UUID] = Field(default_factory=list)
    provider_configs: list[dict[str, Any]] = Field(default_factory=list)
    
    # Evaluation Settings
    judge_config: Optional[dict[str, Any]] = None
    redteam_config: Optional[dict[str, Any]] = None
    regression_detection_enabled: bool = True
    cost_limit_usd: Optional[float] = None
    
    # Baseline
    baseline_id: Optional[UUID] = None
    auto_baseline: bool = False  # Create baseline from first run
    
    # Execution
    max_parallel_cells: int = 4
    timeout_seconds: int = 3600
    retry_failed_cells: bool = True
    max_retries: int = 2
    
    # Release Gate
    gate_config: Optional[dict[str, Any]] = None
    require_human_review: bool = True
    
    # Metadata
    tags: list[str] = Field(default_factory=list)
    created_by: Optional[UUID] = None


class PipelineResult(BaseModel):
    pipeline_id: UUID
    status: PipelineStatus
    config: PipelineConfig
    
    # Execution
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_duration_seconds: Optional[float] = None
    
    # Matrix
    total_cells: int = 0
    completed_cells: int = 0
    failed_cells: int = 0
    
    # Results
    passed_count: int = 0
    failed_count: int = 0
    inconclusive_count: int = 0
    
    # Regressions
    regression_count: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    
    # Cost
    total_cost_usd: float = 0.0
    
    # Gate Decision
    gate_decision: Optional[str] = None
    gate_exit_code: Optional[int] = None
    
    # Release Decision
    release_decision: Optional[str] = None  # READY, WARNING, NEEDS_REVIEW, BLOCKED
    
    # Review
    review_required: bool = False
    review_ids: list[UUID] = Field(default_factory=list)
    
    # Steps
    steps: list[PipelineStep] = Field(default_factory=list)
    
    # Error
    error: Optional[str] = None
    
    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)


class PipelineRun(BaseModel):
    """Persistent pipeline run record."""
    id: UUID = Field(default_factory=uuid4)
    config: PipelineConfig
    status: PipelineStatus = PipelineStatus.QUEUED
    result: Optional[PipelineResult] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[UUID] = None