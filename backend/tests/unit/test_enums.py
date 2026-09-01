import pytest
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
    GateExitCode,
    ModelProvider,
)


def test_test_case_category_values():
    assert TestCaseCategory.SMOKE.value == "smoke"
    assert TestCaseCategory.SAFETY.value == "safety"
    assert TestCaseCategory.JAILBREAK.value == "jailbreak"
    assert TestCaseCategory.PROMPT_INJECTION.value == "prompt_injection"
    assert TestCaseCategory.PII.value == "pii"
    assert TestCaseCategory.CUSTOM.value == "custom"


def test_test_case_severity_values():
    assert TestCaseSeverity.CRITICAL.value == "critical"
    assert TestCaseSeverity.HIGH.value == "high"
    assert TestCaseSeverity.MEDIUM.value == "medium"
    assert TestCaseSeverity.LOW.value == "low"


def test_expected_behavior_type_values():
    assert ExpectedBehaviorType.EXACT_MATCH.value == "exact_match"
    assert ExpectedBehaviorType.REGEX_MATCH.value == "regex_match"
    assert ExpectedBehaviorType.KEYWORD_MATCH.value == "keyword_match"
    assert ExpectedBehaviorType.REFUSAL.value == "refusal"
    assert ExpectedBehaviorType.LLM_RUBRIC.value == "llm_rubric"


def test_verdict_values():
    assert Verdict.PASS.value == "PASS"
    assert Verdict.FAIL.value == "FAIL"
    assert Verdict.INCONCLUSIVE.value == "INCONCLUSIVE"


def test_run_status_values():
    assert RunStatus.QUEUED.value == "queued"
    assert RunStatus.RUNNING.value == "running"
    assert RunStatus.COMPLETED.value == "completed"
    assert RunStatus.FAILED.value == "failed"
    assert RunStatus.REVIEW_REQUIRED.value == "review_required"


def test_severity_level_values():
    assert SeverityLevel.CRITICAL.value == "critical"
    assert SeverityLevel.HIGH.value == "high"
    assert SeverityLevel.MEDIUM.value == "medium"
    assert SeverityLevel.LOW.value == "low"


def test_review_label_values():
    assert ReviewLabel.CONFIRMED_REGRESSION.value == "confirmed_regression"
    assert ReviewLabel.FALSE_POSITIVE.value == "false_positive"
    assert ReviewLabel.NON_BLOCKING.value == "non_blocking"
    assert ReviewLabel.NEEDS_ESCALATION.value == "needs_escalation"


def test_gate_decision_values():
    assert GateDecision.PASS.value == "PASS"
    assert GateDecision.WARN.value == "WARN"
    assert GateDecision.FAIL.value == "FAIL"
    assert GateDecision.BLOCK.value == "BLOCK"


def test_gate_exit_code_values():
    assert GateExitCode.PASS.value == 0
    assert GateExitCode.REGRESSION_FAILURE.value == 1
    assert GateExitCode.INFRASTRUCTURE_FAILURE.value == 2


def test_model_provider_values():
    assert ModelProvider.OPENAI.value == "openai"
    assert ModelProvider.ANTHROPIC.value == "anthropic"
    assert ModelProvider.LOCAL.value == "local"
    assert ModelProvider.MOCK.value == "mock"