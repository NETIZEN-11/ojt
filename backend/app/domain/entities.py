from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.domain.enums import (
    AgentStatus,
    ExecutionStatus,
    ExpectedBehaviorType,
    PromptVersionStatus,
    ReviewLabel,
    ReviewStatus,
    RunStatus,
    SeverityLevel,
    TestCaseCategory,
    TestCaseSeverity,
    Verdict,
)
from app.domain.value_objects import (
    ExpectedBehavior,
    TestCaseMetadata,
)


class TestCase(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    suite_id: UUID
    version: int = 1
    test_case_id: str
    category: TestCaseCategory
    severity: TestCaseSeverity
    input: str
    expected_behavior: ExpectedBehavior
    metadata: TestCaseMetadata = Field(default_factory=TestCaseMetadata)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: UUID | None = None
    is_active: bool = True


class TestSuite(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str | None = None
    version: int = 1
    test_cases: list[TestCase] = []
    schema_version: str = "1.0"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: UUID | None = None
    is_active: bool = True


class TargetAgent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str | None = None
    endpoint_url: str
    auth_config: dict[str, Any] = {}
    request_template: dict[str, Any] = {}
    response_extraction: dict[str, Any] = {}
    timeout_seconds: int = 30
    max_retries: int = 3
    allowed: bool = True
    status: AgentStatus = AgentStatus.ACTIVE
    health_check_url: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: UUID | None = None


class Run(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    target_agent_id: UUID
    suite_id: UUID
    suite_version: int
    baseline_id: UUID | None = None
    status: RunStatus = RunStatus.QUEUED
    framework_version: str = "1.0.0"
    model_versions: dict[str, str] = {}
    prompt_versions: dict[str, str] = {}
    config_snapshot: dict[str, Any] = {}
    started_at: datetime | None = None
    completed_at: datetime | None = None
    total_tests: int = 0
    passed_count: int = 0
    failed_count: int = 0
    inconclusive_count: int = 0
    regression_count: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    total_cost_usd: float = 0.0
    total_latency_ms: int = 0
    error_message: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: UUID | None = None


class Execution(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    test_case_id: UUID
    status: ExecutionStatus = ExecutionStatus.QUEUED
    target_request: dict[str, Any] | None = None
    target_response: dict[str, Any] | None = None
    tool_calls: list[dict[str, Any]] = []
    started_at: datetime | None = None
    completed_at: datetime | None = None
    latency_ms: int = 0
    error: str | None = None
    retry_count: int = 0


class Result(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    execution_id: UUID
    run_id: UUID
    test_case_id: UUID
    verdict: Verdict
    confidence: float
    matcher_used: ExpectedBehaviorType | None = None
    judge_output: dict[str, Any] | None = None
    second_judge_output: dict[str, Any] | None = None
    judge_agreement: bool = True
    evidence: list[dict[str, Any]] = []
    execution_time_ms: int
    tokens_used: int = 0
    estimated_cost: float = 0.0
    errors: list[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Baseline(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    suite_id: UUID
    suite_version: int
    run_id: UUID
    name: str
    description: str | None = None
    framework_version: str
    model_versions: dict[str, str]
    prompt_versions: dict[str, str]
    approved_by: UUID
    approved_at: datetime
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class BaselineItem(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    baseline_id: UUID
    test_case_id: UUID
    verdict: Verdict
    confidence: float
    evidence: list[dict[str, Any]] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Regression(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    baseline_id: UUID
    test_case_id: UUID
    previous_verdict: Verdict
    current_verdict: Verdict
    regression_type: str
    severity: SeverityLevel
    evidence: list[dict[str, Any]] = []
    acknowledged: bool = False
    acknowledged_by: UUID | None = None
    acknowledged_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SeverityFinding(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    regression_id: UUID
    level: SeverityLevel
    rationale: str
    deterministic_override: bool = False
    categories: list[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ReviewQueue(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    regression_id: UUID
    run_id: UUID
    severity: SeverityLevel
    confidence: float
    category: str
    status: ReviewStatus = ReviewStatus.PENDING
    assigned_to: UUID | None = None
    label: ReviewLabel | None = None
    reviewer_notes: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: datetime | None = None


class ReviewLabelRecord(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    review_id: UUID
    label: ReviewLabel
    reviewer_id: UUID
    rationale: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AuditLog(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID | None = None
    action: str
    resource_type: str
    resource_id: UUID | None = None
    details: dict[str, Any] = {}
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ModelConfig(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    provider: str
    model_name: str
    model_version: str
    role: str
    config: dict[str, Any] = {}
    is_active: bool = True
    is_default: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PromptVersion(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    prompt_type: str
    version: str
    content: str
    variables: list[str] = []
    status: PromptVersionStatus = PromptVersionStatus.DRAFT
    created_by: UUID
    created_at: datetime = Field(default_factory=datetime.utcnow)
    promoted_at: datetime | None = None
    promoted_by: UUID | None = None


class AttackTaxonomy(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    category: str
    subcategory: str | None = None
    technique: str
    description: str
    examples: list[str] = []
    severity: TestCaseSeverity
    tags: list[str] = []
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class EmbeddingDocument(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    collection: str
    content: str
    metadata: dict[str, Any] = {}
    embedding: list[float] | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FeatureFlag(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    enabled: bool
    description: str
    rollout_percentage: int = 100
    metadata: dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Notification(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    type: str
    title: str
    message: str
    data: dict[str, Any] = {}
    read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
