import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime

from app.evaluation.regression.detector import RegressionDetector
from app.domain.enums import Verdict, RegressionType, SeverityLevel
from app.domain.value_objects import RegressionFinding, EvidenceItem
from app.models.regression import Regression
from app.models.baseline import BaselineItem
from app.models.run import Result


@pytest.fixture
def mock_result_repo():
    return AsyncMock()


@pytest.fixture
def mock_baseline_repo():
    return AsyncMock()


@pytest.fixture
def mock_baseline_item_repo():
    return AsyncMock()


@pytest.fixture
def mock_regression_repo():
    return AsyncMock()


@pytest.fixture
def detector(mock_result_repo, mock_baseline_repo, mock_baseline_item_repo, mock_regression_repo):
    return RegressionDetector(
        mock_result_repo,
        mock_baseline_repo,
        mock_baseline_item_repo,
        mock_regression_repo,
    )


@pytest.fixture
def run_id():
    return uuid4()


@pytest.fixture
def baseline_id():
    return uuid4()


@pytest.fixture
def baseline():
    return MagicMock(
        id=baseline_id,
        run_id=uuid4(),
    )


class TestRegressionDetector:
    @pytest.mark.asyncio
    async def test_pass_to_fail_regression(self, detector, run_id, baseline_id, baseline):
        test_case_id = uuid4()
        
        # Mock baseline
        detector.baseline_repo.get = AsyncMock(return_value=baseline)
        detector.baseline_item_repo.list_by_baseline = AsyncMock(return_value=[
            MagicMock(
                test_case_id=test_case_id,
                verdict=Verdict.PASS,
                confidence=0.9,
            )
        ])
        
        # Mock current results
        detector.result_repo.list_by_run = AsyncMock(return_value=[
            MagicMock(
                test_case_id=test_case_id,
                verdict=Verdict.FAIL,
                confidence=0.8,
            )
        ])
        
        # Mock regression creation
        detector.regression_repo.create = AsyncMock(return_value=MagicMock())
        
        findings = await detector.detect_regressions(run_id, baseline_id)
        
        assert len(findings) == 1
        finding = findings[0]
        assert finding.test_case_id == str(test_case_id)
        assert finding.previous_verdict == Verdict.PASS
        assert finding.current_verdict == Verdict.FAIL
        assert finding.regression_type == RegressionType.PASS_TO_FAIL.value

    @pytest.mark.asyncio
    async def test_pass_to_inconclusive_regression(self, detector, run_id, baseline_id, baseline):
        test_case_id = uuid4()
        
        detector.baseline_repo.get = AsyncMock(return_value=baseline)
        detector.baseline_item_repo.list_by_baseline = AsyncMock(return_value=[
            MagicMock(test_case_id=test_case_id, verdict=Verdict.PASS, confidence=0.9)
        ])
        detector.result_repo.list_by_run = AsyncMock(return_value=[
            MagicMock(test_case_id=test_case_id, verdict=Verdict.INCONCLUSIVE, confidence=0.5)
        ])
        detector.regression_repo.create = AsyncMock(return_value=MagicMock())
        
        findings = await detector.detect_regressions(run_id, baseline_id)
        
        assert len(findings) == 1
        finding = findings[0]
        assert finding.regression_type == RegressionType.PASS_TO_INCONCLUSIVE.value

    @pytest.mark.asyncio
    async def test_fail_to_fail_no_regression(self, detector, run_id, baseline_id, baseline):
        test_case_id = uuid4()
        
        detector.baseline_repo.get = AsyncMock(return_value=baseline)
        detector.baseline_item_repo.list_by_baseline = AsyncMock(return_value=[
            MagicMock(test_case_id=test_case_id, verdict=Verdict.FAIL, confidence=0.8)
        ])
        detector.result_repo.list_by_run = AsyncMock(return_value=[
            MagicMock(test_case_id=test_case_id, verdict=Verdict.FAIL, confidence=0.7)
        ])
        detector.regression_repo.create = AsyncMock()
        
        findings = await detector.detect_regressions(run_id, baseline_id)
        
        assert len(findings) == 0

    @pytest.mark.asyncio
    async def test_new_test_case_regression(self, detector, run_id, baseline_id, baseline):
        test_case_id = uuid4()
        
        detector.baseline_repo.get = AsyncMock(return_value=baseline)
        detector.baseline_item_repo.list_by_baseline = AsyncMock(return_value=[])
        detector.result_repo.list_by_run = AsyncMock(return_value=[
            MagicMock(test_case_id=test_case_id, verdict=Verdict.FAIL, confidence=0.8)
        ])
        detector.regression_repo.create = AsyncMock(return_value=MagicMock())
        
        findings = await detector.detect_regressions(run_id, baseline_id)
        
        assert len(findings) == 1
        finding = findings[0]
        assert finding.regression_type == RegressionType.NEW_FAILURE.value
        assert finding.previous_verdict == Verdict.INCONCLUSIVE


class TestRegressionClassification:
    @pytest.mark.asyncio
    async def test_classify_regression_types(self, detector):
        assert detector._classify_regression(Verdict.PASS, Verdict.FAIL) == RegressionType.PASS_TO_FAIL
        assert detector._classify_regression(Verdict.PASS, Verdict.INCONCLUSIVE) == RegressionType.PASS_TO_INCONCLUSIVE
        assert detector._classify_regression(Verdict.FAIL, Verdict.FAIL) == RegressionType.FAIL_TO_FAIL
        assert detector._classify_regression(Verdict.FAIL, Verdict.PASS) == RegressionType.FAIL_TO_PASS
        assert detector._classify_regression(Verdict.INCONCLUSIVE, Verdict.FAIL) == RegressionType.INCONCLUSIVE_TO_FAIL

    @pytest.mark.asyncio
    async def test_determine_base_severity(self, detector):
        assert detector._determine_base_severity(Verdict.PASS, Verdict.FAIL, RegressionType.PASS_TO_FAIL) == SeverityLevel.HIGH
        assert detector._determine_base_severity(Verdict.PASS, Verdict.INCONCLUSIVE, RegressionType.PASS_TO_INCONCLUSIVE) == SeverityLevel.MEDIUM
        assert detector._determine_base_severity(Verdict.FAIL, Verdict.FAIL, RegressionType.FAIL_TO_FAIL) == SeverityLevel.LOW
        assert detector._determine_base_severity(Verdict.FAIL, Verdict.PASS, RegressionType.FAIL_TO_PASS) == SeverityLevel.LOW