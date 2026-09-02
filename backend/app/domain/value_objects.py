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
    source: str
    text: str
    metadata: dict[str, Any] = {}


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
    def validate_evidence_not_empty(cls, v: list[EvidenceItem]) -> list[EvidenceItem]:
        if not v:
            raise ValueError("Evidence list cannot be empty for accepted verdict")
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
