from app.domain.enums import (
    GateDecision,
    RegressionType,
    SeverityLevel,
    TestCaseCategory,
    Verdict,
)
from app.domain.policies import (
    classify_severity_deterministic,
    evaluate_gate,
    should_block_merge,
)
from app.domain.value_objects import GateResult, RegressionFinding


def test_critical_severity_override_pii():
    finding = RegressionFinding(
        test_case_id="test",
        previous_verdict=Verdict.PASS,
        current_verdict=Verdict.FAIL,
        regression_type=RegressionType.PASS_TO_FAIL,
        severity=SeverityLevel.MEDIUM,
        evidence=[],
        baseline_run_id="baseline",
        current_run_id="current",
    )

    result = classify_severity_deterministic(finding, TestCaseCategory.PII)

    assert result.level == SeverityLevel.CRITICAL
    assert result.deterministic_override is True
    assert "PII" in result.rationale


def test_critical_severity_override_safety():
    finding = RegressionFinding(
        test_case_id="test",
        previous_verdict=Verdict.PASS,
        current_verdict=Verdict.FAIL,
        regression_type=RegressionType.PASS_TO_FAIL,
        severity=SeverityLevel.MEDIUM,
        evidence=[],
        baseline_run_id="baseline",
        current_run_id="current",
    )

    result = classify_severity_deterministic(finding, TestCaseCategory.SAFETY)

    assert result.level == SeverityLevel.CRITICAL
    assert result.deterministic_override is True


def test_high_severity_override_jailbreak():
    finding = RegressionFinding(
        test_case_id="test",
        previous_verdict=Verdict.PASS,
        current_verdict=Verdict.FAIL,
        regression_type=RegressionType.PASS_TO_FAIL,
        severity=SeverityLevel.MEDIUM,
        evidence=[],
        baseline_run_id="baseline",
        current_run_id="current",
    )

    result = classify_severity_deterministic(finding, TestCaseCategory.JAILBREAK)

    assert result.level == SeverityLevel.CRITICAL
    assert result.deterministic_override is True


def test_medium_severity_pass_to_fail():
    finding = RegressionFinding(
        test_case_id="test",
        previous_verdict=Verdict.PASS,
        current_verdict=Verdict.FAIL,
        regression_type=RegressionType.PASS_TO_FAIL,
        severity=SeverityLevel.MEDIUM,
        evidence=[],
        baseline_run_id="baseline",
        current_run_id="current",
    )

    result = classify_severity_deterministic(finding, TestCaseCategory.CUSTOM)

    assert result.level == SeverityLevel.MEDIUM
    assert result.deterministic_override is False


def test_gate_block_critical():
    findings = [
        RegressionFinding(
            test_case_id="test1",
            previous_verdict=Verdict.PASS,
            current_verdict=Verdict.FAIL,
            regression_type=RegressionType.PASS_TO_FAIL,
            severity=SeverityLevel.CRITICAL,
            evidence=[],
            baseline_run_id="baseline",
            current_run_id="current",
        )
    ]

    result = evaluate_gate(findings, 0, False)

    assert result.decision == GateDecision.BLOCK
    assert result.exit_code == 1
    assert result.critical_count == 1


def test_gate_block_high():
    findings = [
        RegressionFinding(
            test_case_id="test1",
            previous_verdict=Verdict.PASS,
            current_verdict=Verdict.FAIL,
            regression_type=RegressionType.PASS_TO_FAIL,
            severity=SeverityLevel.HIGH,
            evidence=[],
            baseline_run_id="baseline",
            current_run_id="current",
        )
    ]

    result = evaluate_gate(findings, 0, False)

    assert result.decision == GateDecision.BLOCK
    assert result.exit_code == 1


def test_gate_warn_medium():
    findings = [
        RegressionFinding(
            test_case_id="test1",
            previous_verdict=Verdict.PASS,
            current_verdict=Verdict.FAIL,
            regression_type=RegressionType.PASS_TO_FAIL,
            severity=SeverityLevel.MEDIUM,
            evidence=[],
            baseline_run_id="baseline",
            current_run_id="current",
        )
    ]

    result = evaluate_gate(findings, 0, False)

    assert result.decision == GateDecision.WARN
    assert result.exit_code == 0


def test_gate_fail_inconclusive():
    findings = []

    result = evaluate_gate(findings, 2, False)

    assert result.decision == GateDecision.FAIL
    assert result.exit_code == 1
    assert result.inconclusive_count == 2


def test_gate_fail_infrastructure():
    findings = []

    result = evaluate_gate(findings, 0, True)

    assert result.decision == GateDecision.FAIL
    assert result.exit_code == 2
    assert result.infrastructure_failure is True


def test_gate_pass_no_regressions():
    findings = []

    result = evaluate_gate(findings, 0, False)

    assert result.decision == GateDecision.PASS
    assert result.exit_code == 0


def test_should_block_merge():
    block_result = GateResult(
        decision=GateDecision.BLOCK,
        exit_code=1,
        regressions=[],
    )
    fail_result = GateResult(
        decision=GateDecision.FAIL,
        exit_code=1,
        regressions=[],
    )
    warn_result = GateResult(
        decision=GateDecision.WARN,
        exit_code=0,
        regressions=[],
    )
    pass_result = GateResult(
        decision=GateDecision.PASS,
        exit_code=0,
        regressions=[],
    )

    assert should_block_merge(block_result) is True
    assert should_block_merge(fail_result) is True
    assert should_block_merge(warn_result) is False
    assert should_block_merge(pass_result) is False
