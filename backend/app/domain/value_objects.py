from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.domain.enums import (
    ExpectedBehaviorType,
    SeverityLevel,
    Verdict,
)


class MatcherConfig(BaseModel):
    type: ExpectedBehaviorType | None = None
    pattern: str | None = None
    keywords: list[str] | None = None
    case_sensitive: bool = False
    regex_timeout_ms: int = 1000
    expected_keys: list[str] | None = None
    required_fields: list[str] | None = None

    @field_validator("pattern")
    @classmethod
    def validate_regex(cls, v: str | None) -> str | None:
        if v is not None:
            import re

            try:
                re.compile(v)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern: {e}")
        return v


class LLMRubricCriterion(BaseModel):
    name: str
    description: str
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    pass_threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class LLMRubric(BaseModel):
    criteria: list[LLMRubricCriterion]
    overall_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    require_evidence: bool = True


class TestCaseMetadata(BaseModel):
    tags: list[str] = []
    author: str | None = None
    description: str | None = None
    references: list[str] = []
    custom: dict[str, Any] = {}


class ExpectedBehavior(BaseModel):
    type: ExpectedBehaviorType
    matcher: MatcherConfig | None = None
    rubric: LLMRubric | None = None
    custom_validator: str | None = None


class EvidenceItem(BaseModel):
    """Structured evidence item for reproducibility and traceability."""
    source: str
    text: str
    # Traceability fields
    trace_id: str | None = None
    span_id: str | None = None
    # Metadata
    metadata: dict[str, Any] = {}
    # Provenance
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    collected_by: str | None = None  # component that collected this evidence
    # Integrity
    content_hash: str | None = None  # SHA256 of text for integrity verification


class CriteriaResult(BaseModel):
    criterion: str
    passed: bool
    evidence: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class JudgeOutput(BaseModel):
    verdict: Verdict
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(min_length=1)
    evidence: list[EvidenceItem] = []
    criteria_results: list[CriteriaResult] = []

    @field_validator("evidence")
    @classmethod
    def validate_evidence_not_empty(cls, v: list[EvidenceItem], info) -> list[EvidenceItem]:
        # Only require evidence for PASS/FAIL verdicts, not INCONCLUSIVE
        verdict = info.data.get("verdict")
        if verdict in (Verdict.PASS, Verdict.FAIL) and not v:
            raise ValueError(f"Evidence list cannot be empty for {verdict} verdict")
        return v

    @field_validator("criteria_results")
    @classmethod
    def validate_criteria_consistency(cls, v: list[CriteriaResult]) -> list[CriteriaResult]:
        for criterion in v:
            if criterion.passed and criterion.confidence < 0.5:
                raise ValueError(f"Criterion '{criterion.criterion}' passed but confidence too low")
        return v


class ScoringResult(BaseModel):
    test_case_id: str
    verdict: Verdict
    confidence: float = Field(ge=0.0, le=1.0)
    matcher_used: ExpectedBehaviorType | None = None
    judge_output: JudgeOutput | None = None
    second_judge_output: JudgeOutput | None = None
    judge_agreement: bool = True
    evidence: list[EvidenceItem] = []
    execution_time_ms: int
    tokens_used: int = 0
    estimated_cost: float = 0.0
    errors: list[str] = []


class RegressionFinding(BaseModel):
    test_case_id: str
    previous_verdict: Verdict
    current_verdict: Verdict
    regression_type: str
    severity: SeverityLevel
    evidence: list[EvidenceItem] = []
    baseline_run_id: str
    current_run_id: str


class SeverityClassification(BaseModel):
    level: SeverityLevel
    rationale: str
    deterministic_override: bool = False
    categories: list[str] = []


class GateResult(BaseModel):
    decision: str
    exit_code: int
    regressions: list[RegressionFinding] = []
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    inconclusive_count: int = 0
    infrastructure_failure: bool = False
    summary: str = ""


class CostBreakdown(BaseModel):
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    by_model: dict[str, dict[str, Any]] = {}
    by_provider: dict[str, dict[str, Any]] = {}


class EvidencePackage(BaseModel):
    """Complete evidence package for a single evaluation cell - immutable and reproducible."""
    evaluation_id: str
    test_case_id: str
    cell_id: str | None = None
    trace_id: str
    span_id: str
    
    # Input/Output
    test_input: str
    expected_behavior: str
    actual_response: str
    
    # Evidence
    assertion_evidence: list[EvidenceItem] = []
    judge_evidence: list[EvidenceItem] = []
    redteam_evidence: list[EvidenceItem] = []
    
    # Results
    assertion_result: dict[str, Any] | None = None
    judge_result: dict[str, Any] | None = None
    redteam_result: dict[str, Any] | None = None
    
    # Final verdict
    final_verdict: str
    final_confidence: float
    final_severity: str | None = None
    
    # Metadata
    execution_time_ms: int
    tokens_used: int
    estimated_cost: float
    model_info: dict[str, str] = {}
    provider_info: dict[str, str] = {}
    prompt_version: str | None = None
    dataset_version: str | None = None
    
    # Timestamps
    started_at: datetime
    completed_at: datetime
    
    # Integrity
    package_hash: str | None = None  # SHA256 of the entire package for integrity
    
    # Reproducibility
    config_snapshot: dict[str, Any] = {}
    reproducibility_verified: bool = False
    reproducibility_check_at: datetime | None = None
    reproducibility_check_result: dict[str, Any] | None = None
