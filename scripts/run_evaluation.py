#!/usr/bin/env python3
"""Run an evaluation from the command line."""

import asyncio
import argparse
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.repositories.agents import TargetAgentRepository
from app.repositories.suites import TestSuiteRepository
from app.repositories.runs import RunRepository, ExecutionRepository, ResultRepository
from app.repositories.baselines import BaselineRepository
from app.services.execution_service import ExecutionService
from app.services.scoring_service import ScoringService
from app.evaluation.regression.detector import RegressionDetector
from app.evaluation.severity.classifier import SeverityClassifier
from app.evaluation.gate.evaluator import GateEvaluator
from app.models.run import Run
from app.domain.enums import RunStatus

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/redteam"

async def run_evaluation(agent_name: str, suite_name: str, baseline_name: str = None):
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        agent_repo = TargetAgentRepository(session)
        suite_repo = TestSuiteRepository(session)
        run_repo = RunRepository(session)
        execution_repo = ExecutionRepository(session)
        result_repo = ResultRepository(session)
        baseline_repo = BaselineRepository(session)

        # Find agent
        agent = await agent_repo.get_by_name(agent_name)
        if not agent:
            print(f"❌ Agent '{agent_name}' not found")
            return False

        # Find suite
        suites = await suite_repo.list(filters={"name": suite_name, "is_active": True})
        if not suites:
            print(f"❌ Suite '{suite_name}' not found")
            return False
        suite = suites[0]

        # Find baseline
        baseline = None
        if baseline_name:
            baselines = await baseline_repo.list(filters={"suite_id": suite.id, "is_active": True})
            baseline = next((b for b in baselines if b.name == baseline_name), None)
            if not baseline:
                print(f"❌ Baseline '{baseline_name}' not found")
                return False
        else:
            baseline = await baseline_repo.get_active_for_suite(suite.id)

        print(f"🔬 Starting evaluation:")
        print(f"   Agent: {agent.name} ({agent.id})")
        print(f"   Suite: {suite.name} v{suite.version}")
        print(f"   Baseline: {baseline.name if baseline else 'None'}")

        # Create run
        run = Run(
            target_agent_id=agent.id,
            suite_id=suite.id,
            suite_version=suite.version,
            baseline_id=baseline.id if baseline else None,
            framework_version="1.0.0",
            model_versions={},
            prompt_versions={},
            config_snapshot={},
            status=RunStatus.QUEUED,
        )
        run = await run_repo.create(run)
        print(f"   Run ID: {run.id}")

        # Execute
        execution_service = ExecutionService(
            run_repo, execution_repo, result_repo, agent_repo, suite_repo
        )
        
        print("📋 Executing tests...")
        await execution_service.execute_run(run.id)
        
        print("📊 Scoring results...")
        scoring_service = ScoringService(execution_repo, result_repo, suite_repo)
        await scoring_service.score_run(run.id)

        # Regression detection
        if baseline:
            print("🔍 Detecting regressions...")
            from app.repositories.baselines import BaselineItemRepository
            baseline_item_repo = BaselineItemRepository(session)
            regression_repo = RegressionRepository(session)
            
            detector = RegressionDetector(
                result_repo, baseline_repo, baseline_item_repo, regression_repo
            )
            findings = await detector.detect_regressions(run.id, baseline.id)

            print("⚖️  Classifying severity...")
            classifier = SeverityClassifier(suite_repo)
            for finding in findings:
                classification = await classifier.classify(finding)
                finding.severity = classification.level

            print("🚪 Evaluating gate...")
            gate_evaluator = GateEvaluator(run_repo, result_repo, regression_repo)
            gate_result = await gate_evaluator.evaluate(run.id)

            print(f"\n📊 Results:")
            print(f"   Gate Decision: {gate_result.decision}")
            print(f"   Exit Code: {gate_result.exit_code}")
            print(f"   Critical: {gate_result.critical_count}")
            print(f"   High: {gate_result.high_count}")
            print(f"   Medium: {gate_result.medium_count}")
            print(f"   Low: {gate_result.low_count}")
            print(f"   Inconclusive: {gate_result.inconclusive_count}")

            if gate_result.decision in ("BLOCK", "FAIL"):
                print("\n❌ GATE FAILED - Deployment blocked")
                return False
            else:
                print("\n✅ GATE PASSED")
                return True
        else:
            print("\n✅ Evaluation complete (no baseline for regression detection)")
            return True

    await engine.dispose()

def main():
    parser = argparse.ArgumentParser(description="Run an evaluation")
    parser.add_argument("--agent", required=True, help="Target agent name")
    parser.add_argument("--suite", required=True, help="Test suite name")
    parser.add_argument("--baseline", help="Baseline name (optional)")
    
    args = parser.parse_args()
    
    success = asyncio.run(run_evaluation(args.agent, args.suite, args.baseline))
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()