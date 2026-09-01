from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
from pydantic import BaseModel, Field
from app.domain.enums import (
    TestCaseCategory,
    TestCaseSeverity,
    ExpectedBehaviorType,
    Verdict,
    RunStatus,
    ExecutionStatus,
    SeverityLevel,
    ReviewLabel,
    ReviewStatus,
    GateDecision,
    AgentStatus,
    PromptVersionStatus,
)
from app.domain.value_objects import (
    MatcherConfig,
    ExpectedBehavior,
    TestCaseMetadata,
    ScoringResult,
    RegressionFinding,
    SeverityClassification,
    GateResult,
    CostBreakdown,
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
    created_by: Optional[UUID] = None
    is_active: bool = True


class TestSuite(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: Optional[str] = None
    version: int = 1
    test_cases: List[TestCase] = []
    schema_version: str = "1.0"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[UUID] = None
    is_active: bool = True


class TargetAgent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: Optional[str] = None
    endpoint_url: str
    auth_config: Dict[str, Any] = {}
    request_template: Dict[str, Any] = {}
    response_extraction: Dict[str, Any] = {}
    timeout_seconds: int = 30
    max_retries: int = 3
    allowed: bool = True
    status: AgentStatus = AgentStatus.ACTIVE
    health_check_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[UUID] = None


class Run(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    target_agent_id: UUID
    suite_id: UUID
    suite_version: int
    baseline_id: Optional[UUID] = None
    status: RunStatus = RunStatus.QUEUED
    framework_version: str = "1.0.0"
    model_versions: Dict[str, str] = {}
    prompt_versions: Dict[str, str] = {}
    config_snapshot: Dict[str, Any] = {}
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
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
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[UUID] = None


class Execution(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    test_case_id: UUID
    status: ExecutionStatus = ExecutionStatus.QUEUED
    target_request: Optional[Dict[str, Any]] = None
    target_response: Optional[Dict[str, Any]] = None
    tool_calls: List[Dict[str, Any]] = []
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    latency_ms: int = 0
    error: Optional[str] = None
    retry_count: int = 0


class Result(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    execution_id: UUID
    run_id: UUID
    test_case_id: UUID
    verdict: Verdict
    confidence: float
    matcher_used: Optional[ExpectedBehaviorType] = None
    judge_output: Optional[Dict[str, Any]] = None
    second_judge_output: Optional[Dict[str, Any]] = None
    judge_agreement: bool = True
    evidence: List[Dict[str, Any]] = []
    execution_time_ms: int
    tokens_used: int = 0
    estimated_cost: float = 0.0
    errors: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Baseline(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    suite_id: UUID
    suite_version: int
    run_id: UUID
    name: str
    description: Optional[str] = None
    framework_version: str
    model_versions: Dict[str, str]
    prompt_versions: Dict[str, str]
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
    evidence: List[Dict[str, Any]] = []
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
    evidence: List[Dict[str, Any]] = []
    acknowledged: bool = False
    acknowledged_by: Optional[UUID] = None
    acknowledged_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SeverityFinding(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    regression_id: UUID
    level: SeverityLevel
    rationale: str
    deterministic_override: bool = False
    categories: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ReviewQueue(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    regression_id: UUID
    run_id: UUID
    severity: SeverityLevel
    confidence: float
    category: str
    status: ReviewStatus = ReviewStatus.PENDING
    assigned_to: Optional[UUID] = None
    label: Optional[ReviewLabel] = None
    reviewer_notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None


class ReviewLabelRecord(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    review_id: UUID
    label: ReviewLabel
    reviewer_id: UUID
    rationale: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AuditLog(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    user_id: Optional[UUID] = None
    action: str
    resource_type: str
    resource_id: Optional[UUID] = None
    details: Dict[str, Any] = {}
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ModelConfig(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    provider: str
    model_name: str
    model_version: str
    role: str
    config: Dict[str, Any] = {}
    is_active: bool = True
    is_default: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PromptVersion(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    prompt_type: str
    version: str
    content: str
    variables: List[str] = []
    status: PromptVersionStatus = PromptVersionStatus.DRAFT
    created_by: UUID
    created_at: datetime = Field(default_factory=datetime.utcnow)
    promoted_at: Optional[datetime] = None
    promoted_by: Optional[UUID] = None


class AttackTaxonomy(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    category: str
    subcategory: Optional[str] = None
    technique: str
    description: str
    examples: List[str] = []
    severity: TestCaseSeverity
    tags: List[str] = []
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class EmbeddingDocument(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    collection: str
    content: str
    metadata: Dict[str, Any] = {}
    embedding: Optional[List[float]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FeatureFlag(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    enabled: bool
    description: str
    rollout_percentage: int = 100
    metadata: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Notification(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    type: str
    title: str
    message: str
    data: Dict[str, Any] = {}
    read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)