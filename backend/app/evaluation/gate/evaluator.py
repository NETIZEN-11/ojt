from uuid import UUID

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.domain.enums import GateDecision, RunStatus
from app.domain.policies import evaluate_gate, should_block_merge
from app.domain.value_objects import GateResult, RegressionFinding
from app.repositories.baselines import RegressionRepository
from app.repositories.runs import ResultRepository, RunRepository

logger = get_logger(__name__)


class GateEvaluator:
    def __init__(
        self,
        run_repo: RunRepository,
        result_repo: ResultRepository,
        regression_repo: RegressionRepository,
    ):
        self.run_repo = run_repo
        self.result_repo = result_repo
        self.regression_repo = regression_repo

    async def evaluate(self, run_id: UUID) -> GateResult:
        run = await self.run_repo.get(run_id)
        if not run:
            raise NotFoundError("Run", str(run_id))

        regressions = await self.regression_repo.list_by_run(run_id)

        findings = []
        for reg in regressions:
            findings.append(
                RegressionFinding(
                    test_case_id=str(reg.test_case_id),
                    previous_verdict=reg.previous_verdict,
                    current_verdict=reg.current_verdict,
                    regression_type=reg.regression_type,
                    severity=reg.severity,
                    evidence=[],  # Evidence loaded separately if needed
                    baseline_run_id=str(reg.baseline_id),
                    current_run_id=str(run_id),
                )
            )

        inconclusive_count = run.inconclusive_count

        gate_result = evaluate_gate(findings, inconclusive_count, infrastructure_failure=False)

        run.status = RunStatus.GATING
        run.regression_count = len(findings)
        run.critical_count = gate_result.critical_count
        run.high_count = gate_result.high_count
        run.medium_count = gate_result.medium_count
        run.low_count = gate_result.low_count

        if gate_result.decision == GateDecision.BLOCK:
            run.status = RunStatus.REVIEW_REQUIRED
        elif gate_result.decision == GateDecision.FAIL:
            run.status = RunStatus.FAILED
        elif gate_result.decision in (GateDecision.PASS, GateDecision.WARN):
            run.status = RunStatus.COMPLETED

        run.completed_at = datetime.utcnow()
        await self.run_repo.session.flush()

        logger.info(
            "gate_evaluated",
            run_id=str(run_id),
            decision=gate_result.decision,
            exit_code=gate_result.exit_code,
        )
        return gate_result

    def should_block(self, gate_result: GateResult) -> bool:
        return should_block_merge(gate_result)
