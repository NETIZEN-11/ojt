import json
from datetime import datetime
from typing import Any
from uuid import UUID

from app.core.config import get_settings
from app.core.exceptions import EvaluationFailureError, LLMSchemaError
from app.core.logging import get_logger
from app.domain.enums import ExecutionStatus, ExpectedBehaviorType, RunStatus, Verdict
from app.domain.value_objects import (
    EvidenceItem,
    ExpectedBehavior,
    JudgeOutput,
    LLMRubric,
    LLMRubricCriterion,
    MatcherConfig,
    ScoringResult,
)
from app.evaluation.judges.fallback_judge import FallbackJudge
from app.evaluation.judges.llm_judge import LLMJudge
from app.evaluation.matchers.exact import ExactMatcher
from app.evaluation.matchers.keyword import KeywordMatcher
from app.evaluation.matchers.refusal import RefusalMatcher
from app.evaluation.matchers.regex import RegexMatcher
from app.models.run import Execution, Result
from app.models.test_suite import TestCase
from app.repositories.runs import ExecutionRepository, ResultRepository
from app.repositories.suites import TestCaseRepository

settings = get_settings()
logger = get_logger(__name__)


class ScoringService:
    def __init__(
        self,
        execution_repo: ExecutionRepository,
        result_repo: ResultRepository,
        case_repo: TestCaseRepository,
    ):
        self.execution_repo = execution_repo
        self.result_repo = result_repo
        self.case_repo = case_repo

        self.matchers = {
            ExpectedBehaviorType.EXACT_MATCH: ExactMatcher(),
            ExpectedBehaviorType.REGEX_MATCH: RegexMatcher(),
            ExpectedBehaviorType.KEYWORD_MATCH: KeywordMatcher(),
            ExpectedBehaviorType.REFUSAL: RefusalMatcher(),
        }
        self.judge = LLMJudge()
        self.fallback_judge = FallbackJudge()

    async def score_run(self, run_id: UUID) -> Run:
        from app.repositories.runs import RunRepository
        run_repo = RunRepository(self.execution_repo.session)
        run = await run_repo.get(run_id)
        if not run:
            raise EvaluationFailureError(f"Run not found: {run_id}")

        run.status = RunStatus.SCORING
        await self.execution_repo.session.flush()

        executions = await self.execution_repo.list_by_run(run_id)

        for execution in executions:
            if execution.status != ExecutionStatus.COMPLETED:
                continue

            test_case = await self.case_repo.get(execution.test_case_id)
            if not test_case:
                continue

            scoring_result = await self._score_execution(execution, test_case)

            result = Result(
                execution_id=execution.id,
                run_id=run.id,
                test_case_id=test_case.id,
                verdict=scoring_result.verdict,
                confidence=scoring_result.confidence,
                matcher_used=scoring_result.matcher_used,
                judge_output=scoring_result.judge_output.model_dump() if scoring_result.judge_output else None,
                second_judge_output=scoring_result.second_judge_output.model_dump() if scoring_result.second_judge_output else None,
                judge_agreement=scoring_result.judge_agreement,
                evidence=[e.model_dump() for e in scoring_result.evidence],
                execution_time_ms=scoring_result.execution_time_ms,
                tokens_used=scoring_result.tokens_used,
                estimated_cost=scoring_result.estimated_cost,
                errors=scoring_result.errors,
            )
            await self.result_repo.create(result)

            if scoring_result.verdict == Verdict.PASS:
                run.passed_count += 1
            elif scoring_result.verdict == Verdict.FAIL:
                run.failed_count += 1
            else:
                run.inconclusive_count += 1

            run.total_cost_usd += scoring_result.estimated_cost
            run.total_latency_ms += scoring_result.execution_time_ms

        run.status = RunStatus.DIFFING
        await self.execution_repo.session.flush()
        return run

    def _build_expected_behavior(self, test_case: TestCase) -> ExpectedBehavior:
        """Build ExpectedBehavior object from TestCase fields."""
        if test_case.expected_behavior_type == ExpectedBehaviorType.LLM_RUBRIC:
            rubric = None
            if test_case.rubric_config:
                criteria = []
                for c in test_case.rubric_config.get("criteria", []):
                    criteria.append(LLMRubricCriterion(
                        name=c["name"],
                        description=c["description"],
                        weight=c.get("weight", 1.0),
                        pass_threshold=c.get("pass_threshold", 0.7),
                    ))
                rubric = LLMRubric(
                    criteria=criteria,
                    overall_threshold=test_case.rubric_config.get("overall_threshold", 0.7),
                    require_evidence=test_case.rubric_config.get("require_evidence", True),
                )
            return ExpectedBehavior(
                type=ExpectedBehaviorType.LLM_RUBRIC,
                rubric=rubric,
            )
        matcher = None
        if test_case.matcher_config:
            mc = test_case.matcher_config
            matcher_type = getattr(mc, "type", None) or test_case.expected_behavior_type
            matcher = MatcherConfig(
                type=matcher_type,
                pattern=getattr(mc, "pattern", None),
                keywords=getattr(mc, "keywords", None),
                case_sensitive=getattr(mc, "case_sensitive", False),
                regex_timeout_ms=getattr(mc, "regex_timeout_ms", 1000),
                expected_keys=getattr(mc, "expected_keys", None),
                required_fields=getattr(mc, "required_fields", None),
            )
        return ExpectedBehavior(
            type=test_case.expected_behavior_type,
            matcher=matcher,
        )

    async def _score_execution(
        self, execution: Execution, test_case: TestCase
    ) -> ScoringResult:
        start_time = datetime.utcnow()

        expected = self._build_expected_behavior(test_case)
        response_text = self._extract_response_text(execution.target_response)

        if expected.type in self.matchers:
            matcher = self.matchers[expected.type]
            verdict, confidence, evidence = await matcher.match(
                response_text, expected.matcher
            )
            return ScoringResult(
                test_case_id=str(test_case.id),
                verdict=verdict,
                confidence=confidence,
                matcher_used=expected.type,
                evidence=evidence,
                execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
            )

        if expected.type == ExpectedBehaviorType.LLM_RUBRIC:
            return await self._score_with_judge(
                execution, test_case, expected, response_text, start_time
            )

        return ScoringResult(
            test_case_id=str(test_case.id),
            verdict=Verdict.INCONCLUSIVE,
            confidence=0.0,
            evidence=[EvidenceItem(source="framework", text="No matcher available for expected behavior type")],
            execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
            errors=["Unsupported expected behavior type"],
        )

    async def _score_with_judge(
        self,
        execution: Execution,
        test_case: TestCase,
        expected: ExpectedBehavior,
        response_text: str,
        start_time: datetime,
    ) -> ScoringResult:
        judge_output = await self.judge.judge(
            test_case.input,
            response_text,
            expected.rubric,
        )

        if not self._validate_judge_output(judge_output):
            if settings.JUDGE_RETRY_ON_SCHEMA_ERROR:
                judge_output = await self.judge.judge(
                    test_case.input,
                    response_text,
                    expected.rubric,
                )
                if not self._validate_judge_output(judge_output):
                    raise LLMSchemaError("primary", settings.PRIMARY_JUDGE_MODEL, ["Schema validation failed after retry"])

        second_judge_output = None
        judge_agreement = True

        if settings.JUDGE_DOUBLE_SCORE:
            second_judge_output = await self.fallback_judge.judge(
                test_case.input,
                response_text,
                expected.rubric,
            )
            if self._validate_judge_output(second_judge_output):
                judge_agreement = judge_output.verdict == second_judge_output.verdict
            else:
                second_judge_output = None

        if not judge_agreement:
            return ScoringResult(
                test_case_id=str(test_case.id),
                verdict=Verdict.INCONCLUSIVE,
                confidence=min(judge_output.confidence, second_judge_output.confidence) if second_judge_output else judge_output.confidence,
                matcher_used=ExpectedBehaviorType.LLM_RUBRIC,
                judge_output=judge_output,
                second_judge_output=second_judge_output,
                judge_agreement=False,
                evidence=judge_output.evidence,
                execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                tokens_used=judge_output.metadata.get("tokens_used", 0),
                estimated_cost=judge_output.metadata.get("estimated_cost", 0.0),
            )

        return ScoringResult(
            test_case_id=str(test_case.id),
            verdict=judge_output.verdict,
            confidence=judge_output.confidence,
            matcher_used=ExpectedBehaviorType.LLM_RUBRIC,
            judge_output=judge_output,
            second_judge_output=second_judge_output,
            judge_agreement=judge_agreement,
            evidence=judge_output.evidence,
            execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
            tokens_used=judge_output.metadata.get("tokens_used", 0),
            estimated_cost=judge_output.metadata.get("estimated_cost", 0.0),
        )

    def _validate_judge_output(self, output: JudgeOutput | None) -> bool:
        if not output:
            return False
        try:
            JudgeOutput.model_validate(output.model_dump())
            return True
        except Exception:
            return False

    def _extract_response_text(self, response: dict[str, Any] | None) -> str:
        if not response:
            return ""
        if isinstance(response, str):
            return response
        if "text" in response:
            return str(response["text"])
        if "response" in response:
            return str(response["response"])
        if "output" in response:
            return str(response["output"])
        if "content" in response:
            return str(response["content"])
        return json.dumps(response)


class MockScoringService(ScoringService):
    async def _score_with_judge(
        self,
        execution: Execution,
        test_case: TestCase,
        expected: ExpectedBehavior,
        response_text: str,
        start_time: datetime,
    ) -> ScoringResult:
        if "safe" in response_text.lower() or "refuse" in response_text.lower() or "cannot" in response_text.lower():
            verdict = Verdict.PASS
        elif "unsafe" in response_text.lower() or "harmful" in response_text.lower() or "hack" in response_text.lower():
            verdict = Verdict.FAIL
        else:
            verdict = Verdict.PASS

        return ScoringResult(
            test_case_id=str(test_case.id),
            verdict=verdict,
            confidence=0.9,
            matcher_used=ExpectedBehaviorType.LLM_RUBRIC,
            evidence=[EvidenceItem(source="mock_judge", text=f"Mock judge verdict: {verdict.value}")],
            execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
        )
