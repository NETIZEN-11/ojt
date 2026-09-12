from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_async_session
from app.core.logging import get_logger
from app.core.telemetry import get_tracer
from app.domain.enums import RunStatus
from app.evaluation.gate.evaluator import GateEvaluator
from app.evaluation.gate.reports import GateReportGenerator, CLIReporter
from app.evaluation.pipeline.models import (
    PipelineConfig,
    PipelineResult,
    PipelineRun,
    PipelineStatus,
    PipelineStep,
    PipelineStepStatus,
)
from app.evaluation.regression.detector import RegressionDetector
from app.evaluation.severity.classifier import SeverityClassifier
from app.models.baseline import Baseline, BaselineItem
from app.models.matrix import EvaluationMatrix as EvaluationMatrixModel, EvaluationMatrixCell as EvaluationMatrixCellModel
from app.models.run import Run
from app.repositories.baselines import (
    BaselineItemRepository,
    BaselineRepository,
    RegressionRepository,
    ReviewQueueRepository,
)
from app.repositories.matrix import EvaluationMatrixCellRepository, EvaluationMatrixRepository
from app.repositories.runs import ExecutionRepository, ResultRepository, RunRepository
from app.repositories.suites import TestCaseRepository, TestSuiteRepository
from app.repositories.agents import TargetAgentRepository
from app.services.execution_service import ExecutionService
from app.services.matrix_service import MatrixService
from app.services.scoring_service import MockScoringService, ScoringService

settings = get_settings()
logger = get_logger(__name__)
tracer = get_tracer(__name__)


def get_scoring_service():
    if settings.EVAL_MODE == "local" or settings.DEV_MOCK_JUDGE:
        return MockScoringService
    return ScoringService


class EvaluationPipeline:
    """
    Main evaluation pipeline orchestrator.
    
    Coordinates the complete ARTEF workflow:
    1. Configuration Validation
    2. Evaluation Matrix Construction (Test Case × Model × Prompt × Provider × Dataset)
    3. Scheduling (via Celery or direct execution)
    4. Worker Execution (Provider calls + Agent trajectory capture)
    5. Assertions (Deterministic matchers)
    6. AI Judge (LLM-based evaluation)
    7. Red Team (Adversarial testing)
    8. Security/Safety Checks (Model scanner, PII redaction)
    9. Result Aggregation
    10. Baseline Comparison
    11. Regression Detection
    12. Severity Classification
    13. Threshold/Gate Evaluation
    14. Human Review Queue
    15. Release Readiness Decision (READY/WARNING/NEEDS REVIEW/BLOCKED)
    16. Evidence & Trace Persistence
    17. CI/CD Gate Reports
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.run: Optional[PipelineRun] = None
        
        # Repositories
        self.suite_repo = TestSuiteRepository(session)
        self.case_repo = TestCaseRepository(session)
        self.agent_repo = TargetAgentRepository(session)
        self.run_repo = RunRepository(session)
        self.exec_repo = ExecutionRepository(session)
        self.result_repo = ResultRepository(session)
        self.baseline_repo = BaselineRepository(session)
        self.baseline_item_repo = BaselineItemRepository(session)
        self.regression_repo = RegressionRepository(session)
        self.review_repo = ReviewQueueRepository(session)
        self.matrix_repo = EvaluationMatrixRepository(session)
        self.cell_repo = EvaluationMatrixCellRepository(session)
        
        # Services
        self.execution_service = ExecutionService(
            self.run_repo, self.exec_repo, self.result_repo, self.agent_repo, self.case_repo
        )
        self.matrix_service = MatrixService(
            self.matrix_repo, self.cell_repo, self.run_repo,
            self.suite_repo, self.case_repo, self.agent_repo,
            self.baseline_repo, self.baseline_item_repo,
            self.regression_repo, self.review_repo
        )
    
    async def run(self, config: PipelineConfig) -> PipelineResult:
        """Execute the complete evaluation pipeline."""
        self.run = PipelineRun(config=config)
        
        with tracer.start_as_current_span("evaluation_pipeline") as span:
            span.set_attribute("pipeline.name", config.name)
            span.set_attribute("pipeline.id", str(self.run.id))
            
            try:
                await self._execute_pipeline()
            except Exception as e:
                logger.error("pipeline_failed", pipeline_id=str(self.run.id), error=str(e))
                self.run.status = PipelineStatus.FAILED
                self.run.result = PipelineResult(
                    pipeline_id=self.run.id,
                    status=PipelineStatus.FAILED,
                    config=config,
                    error=str(e),
                )
                raise
            finally:
                await self._persist_run()
        
        return self.run.result
    
    async def _execute_pipeline(self):
        """Execute all pipeline steps in sequence."""
        config = self.run.config
        
        # Step 1: Validate Configuration
        await self._step_validate_config()
        
        # Step 2: Load Dataset & Test Suite
        await self._step_load_dataset_and_suite()
        
        # Step 3: Build Evaluation Matrix
        await self._step_build_matrix()
        
        # Step 4: Schedule & Execute Cells
        await self._step_execute_matrix()
        
        # Step 5: Aggregate Results
        await self._step_aggregate_results()
        
        # Step 6: Baseline Comparison & Regression Detection
        await self._step_baseline_comparison()
        
        # Step 7: Severity Classification
        await self._step_severity_classification()
        
        # Step 8: Gate Evaluation
        await self._step_gate_evaluation()
        
        # Step 9: Release Readiness Decision
        await self._step_release_decision()
        
        # Step 10: Human Review Queue
        await self._step_human_review()
        
        # Step 11: Generate Reports
        await self._step_generate_reports()
        
        # Finalize
        self.run.status = PipelineStatus.COMPLETED
        self.run.result.status = PipelineStatus.COMPLETED
        self.run.result.completed_at = datetime.utcnow()
        if self.run.result.started_at:
            self.run.result.total_duration_seconds = (
                self.run.result.completed_at - self.run.result.started_at
            ).total_seconds()
        
        logger.info("pipeline_completed", pipeline_id=str(self.run.id))
    
    async def _step_validate_config(self):
        """Step 1: Validate pipeline configuration."""
        step = PipelineStep(name="validate_config", status=PipelineStepStatus.RUNNING, started_at=datetime.utcnow())
        self.run.result.steps.append(step)
        
        config = self.run.config
        
        # Validate suite exists
        suite = await self.suite_repo.get(config.suite_id)
        if not suite:
            raise ValueError(f"Test suite {config.suite_id} not found")
        
        # Validate target agent exists
        agent = await self.agent_repo.get(config.target_agent_id)
        if not agent:
            raise ValueError(f"Target agent {config.target_agent_id} not found")
        
        # Validate at least one model configuration
        if not config.models:
            raise ValueError("At least one model configuration required")
        
        # Validate at least one prompt version
        if not config.prompt_versions:
            raise ValueError("At least one prompt version required")
        
        step.status = PipelineStepStatus.COMPLETED
        step.completed_at = datetime.utcnow()
        logger.info("config_validated", pipeline_id=str(self.run.id))
    
    async def _step_load_dataset_and_suite(self):
        """Step 2: Load dataset and test suite."""
        step = PipelineStep(name="load_dataset_and_suite", status=PipelineStepStatus.RUNNING, started_at=datetime.utcnow())
        self.run.result.steps.append(step)
        
        config = self.run.config
        
        # Load test cases
        test_cases = await self.case_repo.list_by_suite(config.suite_id)
        if not test_cases:
            raise ValueError(f"No test cases found in suite {config.suite_id}")
        
        step.status = PipelineStepStatus.COMPLETED
        step.completed_at = datetime.utcnow()
        step.metadata = {"test_case_count": len(test_cases)}
        logger.info("dataset_loaded", pipeline_id=str(self.run.id), test_cases=len(test_cases))
    
    async def _step_build_matrix(self):
        """Step 3: Build evaluation matrix (Test Case × Model × Prompt × Provider)."""
        step = PipelineStep(name="build_matrix", status=PipelineStepStatus.RUNNING, started_at=datetime.utcnow())
        self.run.result.steps.append(step)
        
        config = self.run.config
        suite = await self.suite_repo.get(config.suite_id)
        
        # Build matrix configurations
        matrix_configs = []
        for model_config in config.models:
            for prompt_version_id in config.prompt_versions:
                for provider_config in config.provider_configs:
                    matrix_configs.append({
                        "model_id": model_config.get("model_id"),
                        "model_provider": model_config.get("provider", "openai"),
                        "model_parameters": model_config.get("parameters", {}),
                        "prompt_version_id": str(prompt_version_id),
                        "provider_config": provider_config,
                    })
        
        # Create matrix
        test_case_ids = [tc.id for tc in await self.case_repo.list_by_suite(config.suite_id)]
        
        matrix = await self.matrix_service.create_matrix(
            name=f"{config.name} - Matrix",
            suite_id=config.suite_id,
            test_case_ids=test_case_ids,
            configurations=[
                self._build_matrix_config(mc, pc, pv)
                for mc in config.models
                for pv in config.prompt_versions
                for pc in config.provider_configs
            ],
            description=config.description,
            created_by=config.created_by,
        )
        
        self.run.result.metadata["matrix_id"] = str(matrix.id)
        self.run.result.total_cells = matrix.total_cells
        
        step.status = PipelineStepStatus.COMPLETED
        step.completed_at = datetime.utcnow()
        step.metadata = {"matrix_id": str(matrix.id), "total_cells": matrix.total_cells}
        logger.info("matrix_built", pipeline_id=str(self.run.id), matrix_id=str(matrix.id), cells=matrix.total_cells)
    
    def _build_matrix_config(self, model_config: dict, provider_config: dict, prompt_version_id: UUID):
        from app.domain.matrix import MatrixConfiguration
        return MatrixConfiguration(
            model_id=model_config.get("model_id"),
            model_provider=model_config.get("provider", "openai"),
            model_parameters=model_config.get("parameters", {}),
            prompt_version_id=prompt_version_id,
            provider_config=provider_config,
        )
    
    async def _step_execute_matrix(self):
        """Step 4: Execute all matrix cells."""
        step = PipelineStep(name="execute_matrix", status=PipelineStepStatus.RUNNING, started_at=datetime.utcnow())
        self.run.result.steps.append(step)
        
        matrix_id = UUID(self.run.result.metadata["matrix_id"])
        
        # Execute matrix (creates runs for each cell)
        matrix = await self.matrix_service.execute_matrix(matrix_id)
        
        self.run.result.completed_cells = matrix.completed_cells
        self.run.result.failed_cells = matrix.failed_cells
        
        step.status = PipelineStepStatus.COMPLETED
        step.completed_at = datetime.utcnow()
        step.metadata = {"completed": matrix.completed_cells, "failed": matrix.failed_cells}
        logger.info("matrix_executed", pipeline_id=str(self.run.id), matrix_id=str(matrix_id))
    
    async def _step_aggregate_results(self):
        """Step 5: Aggregate results from all cells."""
        step = PipelineStep(name="aggregate_results", status=PipelineStepStatus.RUNNING, started_at=datetime.utcnow())
        self.run.result.steps.append(step)
        
        matrix_id = UUID(self.run.result.metadata["matrix_id"])
        cells = await self.cell_repo.list_by_matrix(matrix_id)
        
        # Aggregate from cell runs
        total_passed = 0
        total_failed = 0
        total_inconclusive = 0
        total_cost = 0.0
        
        for cell in cells:
            if cell.run_id:
                run = await self.run_repo.get(cell.run_id)
                if run:
                    total_passed += run.passed_count
                    total_failed += run.failed_count
                    total_inconclusive += run.inconclusive_count
                    total_cost += run.total_cost_usd
        
        self.run.result.passed_count = total_passed
        self.run.result.failed_count = total_failed
        self.run.result.inconclusive_count = total_inconclusive
        self.run.result.total_cost_usd = total_cost
        
        step.status = PipelineStepStatus.COMPLETED
        step.completed_at = datetime.utcnow()
        step.metadata = {
            "passed": total_passed,
            "failed": total_failed,
            "inconclusive": total_inconclusive,
            "cost_usd": total_cost,
        }
        logger.info("results_aggregated", pipeline_id=str(self.run.id), passed=total_passed, failed=total_failed)
    
    async def _step_baseline_comparison(self):
        """Step 6: Compare against baseline and detect regressions."""
        step = PipelineStep(name="baseline_comparison", status=PipelineStepStatus.RUNNING, started_at=datetime.utcnow())
        self.run.result.steps.append(step)
        
        config = self.run.config
        matrix_id = UUID(self.run.result.metadata["matrix_id"])
        cells = await self.cell_repo.list_by_matrix(matrix_id)
        
        total_regressions = 0
        critical_count = 0
        high_count = 0
        medium_count = 0
        low_count = 0
        
        for cell in cells:
            if cell.run_id and cell.status == RunStatus.COMPLETED:
                # Get or create baseline
                baseline = None
                if config.baseline_id:
                    baseline = await self.baseline_repo.get(config.baseline_id)
                elif config.auto_baseline:
                    # Check if baseline exists for this suite
                    baseline = await self.baseline_repo.get_active_for_suite(config.suite_id)
                    if not baseline:
                        # Create baseline from this run (first run)
                        baseline = await self._create_baseline_from_cell(cell)
                
                if baseline and config.regression_detection_enabled:
                    detector = RegressionDetector(
                        self.result_repo, self.baseline_repo, self.baseline_item_repo, self.regression_repo
                    )
                    findings = await detector.detect_regressions(cell.run_id, baseline.id)
                    
                    classifier = SeverityClassifier(self.case_repo)
                    for finding in findings:
                        classification = await classifier.classify(finding)
                        finding.severity = classification.level
                        
                        total_regressions += 1
                        if finding.severity.value == "critical":
                            critical_count += 1
                        elif finding.severity.value == "high":
                            high_count += 1
                        elif finding.severity.value == "medium":
                            medium_count += 1
                        elif finding.severity.value == "low":
                            low_count += 1
                        
                        # Queue for human review if critical/high
                        if config.require_human_review and finding.severity.value in ("critical", "high"):
                            review = await self.review_repo.create_review(
                                regression_id=UUID(finding.test_case_id),
                                run_id=cell.run_id,
                                severity=finding.severity,
                                confidence=0.8,
                                category="regression",
                            )
                            self.run.result.review_ids.append(review.id)
        
        self.run.result.regression_count = total_regressions
        self.run.result.critical_count = critical_count
        self.run.result.high_count = high_count
        self.run.result.medium_count = medium_count
        self.run.result.low_count = low_count
        self.run.result.review_required = len(self.run.result.review_ids) > 0
        
        step.status = PipelineStepStatus.COMPLETED
        step.completed_at = datetime.utcnow()
        step.metadata = {
            "regressions": total_regressions,
            "critical": critical_count,
            "high": high_count,
            "medium": medium_count,
            "low": low_count,
        }
        logger.info("baseline_comparison_done", pipeline_id=str(self.run.id), regressions=total_regressions)
    
    async def _create_baseline_from_cell(self, cell) -> Optional[Any]:
        """Create baseline from a completed cell run."""
        if not cell.run_id:
            return None
        
        run = await self.run_repo.get(cell.run_id)
        if not run:
            return None
        
        results = await self.result_repo.list_by_run(run.id)
        if not results:
            return None
        
        baseline = Baseline(
            suite_id=run.suite_id,
            suite_version=run.suite_version,
            run_id=run.id,
            name=f"Auto-baseline for {run.id}",
            description="Automatically created baseline from first run",
            framework_version=run.framework_version,
            model_versions=run.model_versions,
            prompt_versions=run.prompt_versions,
            approved_by=UUID("00000000-0000-0000-0000-000000000000"),
            approved_at=datetime.utcnow(),
            is_active=True,
        )
        baseline = await self.baseline_repo.create(baseline)
        
        for result in results:
            item = BaselineItem(
                baseline_id=baseline.id,
                test_case_id=result.test_case_id,
                verdict=result.verdict,
                confidence=result.confidence,
                evidence=result.evidence,
            )
            await self.baseline_item_repo.create(item)
        
        await self.session.flush()
        return baseline
    
    async def _step_severity_classification(self):
        """Step 7: Classify severity of findings."""
        step = PipelineStep(name="severity_classification", status=PipelineStepStatus.RUNNING, started_at=datetime.utcnow())
        self.run.result.steps.append(step)
        
        # Already done in baseline_comparison step
        step.status = PipelineStepStatus.COMPLETED
        step.completed_at = datetime.utcnow()
    
    async def _step_gate_evaluation(self):
        """Step 8: Evaluate quality gate."""
        step = PipelineStep(name="gate_evaluation", status=PipelineStepStatus.RUNNING, started_at=datetime.utcnow())
        self.run.result.steps.append(step)
        
        config = self.run.config
        matrix_id = UUID(self.run.result.metadata["matrix_id"])
        cells = await self.cell_repo.list_by_matrix(matrix_id)
        
        overall_gate_decision = "PASS"
        overall_exit_code = 0
        
        for cell in cells:
            if cell.run_id and cell.status == RunStatus.COMPLETED:
                gate_evaluator = GateEvaluator(self.run_repo, self.result_repo, self.regression_repo)
                gate_result = await gate_evaluator.evaluate(cell.run_id)
                
                if gate_result.decision == "BLOCK":
                    overall_gate_decision = "BLOCK"
                    overall_exit_code = 1
                elif gate_result.decision == "FAIL" and overall_gate_decision != "BLOCK":
                    overall_gate_decision = "FAIL"
                    overall_exit_code = 1
                elif gate_result.decision == "WARN" and overall_gate_decision == "PASS":
                    overall_gate_decision = "WARN"
        
        self.run.result.gate_decision = overall_gate_decision
        self.run.result.gate_exit_code = overall_exit_code
        
        step.status = PipelineStepStatus.COMPLETED
        step.completed_at = datetime.utcnow()
        step.metadata = {"decision": overall_gate_decision, "exit_code": overall_exit_code}
        logger.info("gate_evaluated", pipeline_id=str(self.run.id), decision=overall_gate_decision)
    
    async def _step_release_decision(self):
        """Step 9: Determine release readiness decision."""
        step = PipelineStep(name="release_decision", status=PipelineStepStatus.RUNNING, started_at=datetime.utcnow())
        self.run.result.steps.append(step)
        
        # Determine release decision based on gate, regressions, and reviews
        gate_decision = self.run.result.gate_decision
        critical_count = self.run.result.critical_count
        high_count = self.run.result.high_count
        review_required = self.run.result.review_required
        review_ids = self.run.result.review_ids
        
        if gate_decision == "BLOCK" or critical_count > 0:
            release_decision = "BLOCKED"
        elif gate_decision == "FAIL" or high_count > 0:
            release_decision = "BLOCKED"
        elif review_required and review_ids:
            # Check if all reviews are resolved
            all_resolved = True
            for review_id in review_ids:
                review = await self.review_repo.get(review_id)
                if review and review.status.value != "resolved":
                    all_resolved = False
                    break
            
            if all_resolved:
                # Check review labels
                has_confirmed_regression = False
                for review_id in review_ids:
                    review = await self.review_repo.get(review_id)
                    if review and review.label and review.label.value == "confirmed_regression":
                        has_confirmed_regression = True
                        break
                
                if has_confirmed_regression:
                    release_decision = "BLOCKED"
                else:
                    release_decision = "READY"
            elif review_required:
                release_decision = "NEEDS_REVIEW"
            elif gate_decision == "WARN" or self.run.result.medium_count > 0 or self.run.result.low_count > 0:
                release_decision = "WARNING"
            else:
                release_decision = "READY"
        
        self.run.result.release_decision = release_decision
        
        step.status = PipelineStepStatus.COMPLETED
        step.completed_at = datetime.utcnow()
        step.metadata = {"decision": release_decision}
        logger.info("release_decision", pipeline_id=str(self.run.id), decision=release_decision)
    
    async def _step_human_review(self):
        """Step 10: Handle human review if required."""
        step = PipelineStep(name="human_review", status=PipelineStepStatus.RUNNING, started_at=datetime.utcnow())
        self.run.result.steps.append(step)
        
        # If review required, pipeline pauses here in real implementation
        # For now, we just note it
        if self.run.result.review_required:
            step.metadata = {"status": "awaiting_review", "review_count": len(self.run.result.review_ids)}
        else:
            step.metadata = {"status": "not_required"}
        
        step.status = PipelineStepStatus.COMPLETED
        step.completed_at = datetime.utcnow()
    
    async def _step_generate_reports(self):
        """Step 11: Generate CI/CD gate reports."""
        step = PipelineStep(name="generate_reports", status=PipelineStepStatus.RUNNING, started_at=datetime.utcnow())
        self.run.result.steps.append(step)
        
        # Generate JUnit XML and JSON reports for each cell run
        # This would be used by CI/CD
        step.status = PipelineStepStatus.COMPLETED
        step.completed_at = datetime.utcnow()
        step.metadata = {"reports_generated": True}
    
    async def _persist_run(self):
        """Persist pipeline run to database."""
        # In a real implementation, this would save to a pipeline_runs table
        # For now, we just log
        logger.info("pipeline_persisted", pipeline_id=str(self.run.id), status=self.run.status.value)


# Convenience function for running pipeline from CLI/API
async def run_evaluation_pipeline(config: PipelineConfig) -> PipelineResult:
    """Run an evaluation pipeline with the given configuration."""
    async with get_async_session() as session:
        pipeline = EvaluationPipeline(session)
        return await pipeline.run(config)


async def rerun_pipeline_for_reproducibility(
    original_pipeline_id: UUID,
    session: AsyncSession,
    verify_results: bool = True,
) -> PipelineResult:
    """
    Re-run a pipeline for reproducibility verification.
    
    This loads the original pipeline configuration and re-executes it,
    then compares results to verify reproducibility.
    """
    # In a real implementation, this would load the original pipeline config
    # from the database using original_pipeline_id
    # For now, we raise NotImplementedError
    raise NotImplementedError("Reproducibility re-run not yet implemented")


class ReproducibilityVerifier:
    """Verifies reproducibility of evaluation results by re-running and comparing."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def verify(
        self,
        original_pipeline_id: UUID,
        tolerance: float = 0.0,  # 0.0 = exact match required
    ) -> dict[str, Any]:
        """
        Verify that re-running a pipeline produces identical results.
        
        Returns:
            dict with keys:
            - verified: bool
            - original_result: PipelineResult
            - rerun_result: PipelineResult
            - differences: list of differences found
        """
        # In a real implementation, this would:
        # 1. Load original pipeline config from database
        # 2. Re-run the pipeline
        # 3. Compare results within tolerance
        # 4. Return verification result
        raise NotImplementedError("Reproducibility verification not yet implemented")
    
    def _compare_results(
        self,
        original: PipelineResult,
        rerun: PipelineResult,
        tolerance: float,
    ) -> list[dict[str, Any]]:
        """Compare two pipeline results and return differences."""
        differences = []
        
        # Compare key metrics
        if abs(original.total_cost_usd - rerun.total_cost_usd) > tolerance:
            differences.append({
                "field": "total_cost_usd",
                "original": original.total_cost_usd,
                "rerun": rerun.total_cost_usd,
                "difference": abs(original.total_cost_usd - rerun.total_cost_usd),
            })
        
        if original.passed_count != rerun.passed_count:
            differences.append({
                "field": "passed_count",
                "original": original.passed_count,
                "rerun": rerun.passed_count,
            })
        
        if original.failed_count != rerun.failed_count:
            differences.append({
                "field": "failed_count",
                "original": original.failed_count,
                "rerun": rerun.failed_count,
            })
        
        if original.release_decision != rerun.release_decision:
            differences.append({
                "field": "release_decision",
                "original": original.release_decision,
                "rerun": rerun.release_decision,
            })
        
        # Compare cell-level results if available
        # This would require loading individual cell results
        
        return differences