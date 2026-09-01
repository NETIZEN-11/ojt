#!/usr/bin/env python3
"""Run seeded regression benchmark to validate the framework."""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, List

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.repositories.agents import TargetAgentRepository
from app.repositories.suites import TestSuiteRepository, TestCaseRepository
from app.repositories.runs import RunRepository, ExecutionRepository, ResultRepository
from app.repositories.baselines import BaselineRepository, BaselineItemRepository, RegressionRepository
from app.services.execution_service import ExecutionService
from app.services.scoring_service import ScoringService, MockScoringService
from app.evaluation.regression.detector import RegressionDetector
from app.evaluation.severity.classifier import SeverityClassifier
from app.evaluation.gate.evaluator import GateEvaluator
from app.models.run import Run
from app.domain.enums import RunStatus, Verdict, RegressionType, SeverityLevel
from app.providers.target_agent import MockTargetAgentProvider

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/redteam"

async def run_seeded_regression() -> Dict[str, Any]:
    """Run the complete seeded regression benchmark."""
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Get repositories
        agent_repo = TargetAgentRepository(session)
        suite_repo = TestSuiteRepository(session)
        case_repo = TestCaseRepository(session)
        run_repo = RunRepository(session)
        execution_repo = ExecutionRepository(session)
        result_repo = ResultRepository(session)
        baseline_repo = BaselineRepository(session)
        baseline_item_repo = BaselineItemRepository(session)
        regression_repo = RegressionRepository(session)

        # Get or create test agents
        safe_agent = await agent_repo.get_by_name("Safe Agent (Mock)")
        vulnerable_agent = await agent_repo.get_by_name("Vulnerable Agent (Mock)")

        if not safe_agent or not vulnerable_agent:
            print("❌ Required mock agents not found. Run seed_demo_data.py first.")
            return {"success": False, "error": "Mock agents not found"}

        # Get test suites
        suites = await suite_repo.list(filters={"is_active": True})
        if not suites:
            print("❌ No test suites found. Run seed_demo_data.py first.")
            return {"success": False, "error": "Test suites not found"}

        print("🔬 Phase 1: Establishing baseline with safe agent...")
        
        # Create baseline run with safe agent
        baseline_run = Run(
            target_agent_id=safe_agent.id,
            suite_id=suites[0].id,  # Use first suite
            suite_version=suites[0].version,
            framework_version="1.0.0",
            model_versions={},
            prompt_versions={},
            config_snapshot={},
            status=RunStatus.QUEUED,
        )
        baseline_run = await run_repo.create(baseline_run)

        # Execute baseline run
        safe_provider = MockTargetAgentProvider(scenario="safe")
        
        execution_service = ExecutionService(
            run_repo, execution_repo, result_repo, agent_repo, case_repo
        )
        
        # Override the target agent call to use our mock
        async def mock_execute_run(run_id: uuid.UUID):
            run = await run_repo.get(run_id)
            if not run:
                return
            
            test_cases = await case_repo.list_by_suite(run.suite_id)
            run.total_tests = len(test_cases)
            run.status = RunStatus.RUNNING
            run.started_at = datetime.utcnow()
            await session.flush()

            for test_case in test_cases:
                execution = await execution_repo.create({
                    "run_id": run.id,
                    "test_case_id": test_case.id,
                    "status": "completed",
                    "started_at": datetime.utcnow(),
                    "completed_at": datetime.utcnow(),
                    "target_request": {"input": test_case.input},
                    "target_response": await safe_provider.call(test_case.input),
                    "latency_ms": 100,
                })
            
            run.status = RunStatus.SCORING
            await session.flush()
            return run

        await mock_execute_run(baseline_run.id)

        # Score baseline run
        scoring_service = MockScoringService(execution_repo, result_repo, case_repo)
        await scoring_service.score_run(baseline_run.id)

        # Create baseline
        baseline = Baseline(
            suite_id=suites[0].id,
            suite_version=suites[0].version,
            run_id=baseline_run.id,
            name="Initial Baseline",
            description="Baseline established with safe agent",
            framework_version="1.0.0",
            model_versions={},
            prompt_versions={},
            approved_by=uuid.uuid4(),  # Would be real user in production
            approved_at=datetime.utcnow(),
            is_active=True,
        )
        baseline = await baseline_repo.create(baseline)

        # Create baseline items
        baseline_results = await result_repo.list_by_run(baseline_run.id)
        for result in baseline_results:
            item = BaselineItem(
                baseline_id=baseline.id,
                test_case_id=result.test_case_id,
                verdict=result.verdict,
                confidence=result.confidence,
                evidence=result.evidence,
            )
            await baseline_item_repo.create(item)

        print(f"✅ Baseline established: {baseline.id}")

        print("🔬 Phase 2: Running evaluation with vulnerable agent...")
        
        # Create test run with vulnerable agent
        test_run = Run(
            target_agent_id=vulnerable_agent.id,
            suite_id=suites[0].id,
            suite_version=suites[0].version,
            baseline_id=baseline.id,
            framework_version="1.0.0",
            model_versions={},
            prompt_versions={},
            config_snapshot={},
            status=RunStatus.QUEUED,
        )
        test_run = await run_repo.create(test_run)

        # Execute test run with vulnerable provider
        vulnerable_provider = MockTargetAgentProvider(scenario="jailbreak_vulnerable")
        
        async def mock_execute_vulnerable(run_id: uuid.UUID):
            run = await run_repo.get(run_id)
            if not run:
                return
            
            test_cases = await case_repo.list_by_suite(run.suite_id)
            run.total_tests = len(test_cases)
            run.status = RunStatus.RUNNING
            run.started_at = datetime.utcnow()
            await session.flush()

            for test_case in test_cases:
                execution = await execution_repo.create({
                    "run_id": run.id,
                    "test_case_id": test_case.id,
                    "status": "completed",
                    "started_at": datetime.utcnow(),
                    "completed_at": datetime.utcnow(),
                    "target_request": {"input": test_case.input},
                    "target_response": await vulnerable_provider.call(test_case.input),
                    "latency_ms": 100,
                })
            
            run.status = RunStatus.SCORING
            await session.flush()
            return run

        await mock_execute_vulnerable(test_run.id)

        # Score test run
        await scoring_service.score_run(test_run.id)

        print("🔬 Phase 3: Detecting regressions...")
        
        # Detect regressions
        detector = RegressionDetector(
            result_repo, baseline_repo, baseline_item_repo, regression_repo
        )
        findings = await detector.detect_regressions(test_run.id, baseline.id)

        print(f"🔍 Found {len(findings)} potential regressions")

        # Classify severity
        classifier = SeverityClassifier(case_repo)
        for finding in findings:
            classification = await classifier.classify(finding)
            finding.severity = classification.level

        print("🔬 Phase 4: Evaluating CI gate...")
        
        # Evaluate gate
        gate_evaluator = GateEvaluator(run_repo, result_repo, regression_repo)
        gate_result = await gate_evaluator.evaluate(test_run.id)

        print(f"🚪 Gate Decision: {gate_result.decision} (Exit Code: {gate_result.exit_code})")
        print(f"   Critical: {gate_result.critical_count}, High: {gate_result.high_count}")
        print(f"   Medium: {gate_result.medium_count}, Low: {gate_result.low_count}")

        # Verify all seeded regressions detected
        seeded_categories = [TestCaseCategory.JAILBREAK]
        expected_regressions = 0
        detected_regressions = 0
        
        for finding in findings:
            test_case = await case_repo.get(uuid.UUID(finding.test_case_id))
            if test_case and test_case.category in seeded_categories:
                expected_regressions += 1
                if finding.severity in (SeverityLevel.CRITICAL, SeverityLevel.HIGH):
                    detected_regressions += 1

        success = detected_regressions >= expected_regressions and expected_regressions > 0
        
        result = {
            "success": success,
            "baseline_id": str(baseline.id),
            "baseline_run_id": str(baseline_run.id),
            "test_run_id": str(test_run.id),
            "total_findings": len(findings),
            "expected_regressions": expected_regressions,
            "detected_regressions": detected_regressions,
            "gate_decision": gate_result.decision,
            "gate_exit_code": gate_result.exit_code,
            "severity_breakdown": {
                "critical": gate_result.critical_count,
                "high": gate_result.high_count,
                "medium": gate_result.medium_count,
                "low": gate_result.low_count,
            },
        }

        if success:
            print("✅ SEEDED REGRESSION BENCHMARK PASSED")
            print(f"   All {expected_regressions} seeded regressions detected!")
        else:
            print("❌ SEEDED REGRESSION BENCHMARK FAILED")
            print(f"   Expected: {expected_regressions}, Detected: {detected_regressions}")

        return result

    await engine.dispose()

if __name__ == "__main__":
    result = asyncio.run(run_seeded_regression())
    exit(0 if result.get("success") else 1)