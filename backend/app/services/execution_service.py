import copy
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.core.exceptions import (
    PipelineError,
    TargetAgentError,
    TargetAgentTimeoutError,
    TargetAgentUnavailableError,
)
from app.core.logging import get_logger
from app.domain.enums import ExecutionStatus, RunStatus
from app.evaluation.cost.cost_tracker import CostTracker, CostCategory
from app.models.run import Execution, Run
from app.models.target_agent import TargetAgent
from app.models.test_suite import TestCase
from app.repositories.agents import TargetAgentRepository
from app.repositories.runs import ExecutionRepository, ResultRepository, RunRepository
from app.repositories.suites import TestCaseRepository
from app.security.pii_redaction import redact_execution_data, redact_for_storage

settings = get_settings()
logger = get_logger(__name__)


def generate_trace_id() -> str:
    """Generate a new trace ID."""
    return uuid4().hex


def generate_span_id() -> str:
    """Generate a new span ID."""
    return uuid4().hex[:16]


class ExecutionService:
    def __init__(
        self,
        run_repo: RunRepository,
        execution_repo: ExecutionRepository,
        result_repo: ResultRepository,
        agent_repo: TargetAgentRepository,
        case_repo: TestCaseRepository,
    ):
        self.run_repo = run_repo
        self.execution_repo = execution_repo
        self.result_repo = result_repo
        self.agent_repo = agent_repo
        self.case_repo = case_repo
        self.cost_tracker = CostTracker()

    async def execute_run(self, run_id: UUID) -> Run:
        run = await self.run_repo.get(run_id)
        if not run:
            raise PipelineError("Run not found", "execute_run", {"run_id": str(run_id)})

        agent = await self.agent_repo.get(run.target_agent_id)
        if not agent:
            raise PipelineError(
                "Target agent not found", "execute_run", {"agent_id": str(run.target_agent_id)}
            )

        run.status = RunStatus.RUNNING
        run.started_at = datetime.utcnow()
        await self.run_repo.session.flush()

        test_cases = await self.case_repo.list_by_suite(run.suite_id)
        run.total_tests = len(test_cases)
        await self.run_repo.session.flush()

        # Generate trace ID for this run
        run_trace_id = generate_trace_id()
        
        for test_case in test_cases:
            execution = Execution(
                run_id=run.id,
                test_case_id=test_case.id,
                status=ExecutionStatus.RUNNING,
                started_at=datetime.utcnow(),
                trace_id=run_trace_id,
                span_id=generate_span_id(),
            )

            try:
                response = await self._call_target_agent(agent, test_case, run)
                
                # Redact PII BEFORE setting on execution (GDPR compliance)
                request_body = self._build_request(agent, test_case)
                execution_data = {
                    "target_request": request_body,
                    "target_response": response,
                    "tool_calls": response.get("tool_calls") if isinstance(response, dict) else None,
                }
                redacted_data = redact_execution_data(execution_data)
                
                execution.target_request = redacted_data["target_request"]
                execution.target_response = redacted_data["target_response"]
                execution.tool_calls = redacted_data["tool_calls"]
                execution.status = ExecutionStatus.COMPLETED
                execution.completed_at = datetime.utcnow()
                elapsed = execution.completed_at - execution.started_at
                execution.latency_ms = int(elapsed.total_seconds() * 1000)
                
                # Create execution record with already-redacted data
                execution = await self.execution_repo.create(execution)

                # Track cost for target agent call (estimate based on response size)
                response_text = str(response.get("text", response.get("response", str(response))))
                estimated_tokens = len(response_text) // 4  # rough estimate
                if estimated_tokens > 0:
                    await self.cost_tracker.track_cost(
                        category=CostCategory.LLM_INFERENCE,
                        provider=agent.auth_config.get("provider", "target_agent"),
                        model=agent.auth_config.get("model", "unknown"),
                        input_tokens=len(test_case.input) // 4,
                        output_tokens=estimated_tokens,
                        run_id=run.id,
                        test_case_id=test_case.id,
                        metadata={"execution_id": str(execution.id), "agent_name": agent.name},
                    )
            except Exception as e:
                execution.status = ExecutionStatus.FAILED
                execution.completed_at = datetime.utcnow()
                execution.error = str(e)
                execution = await self.execution_repo.create(execution)
                logger.exception(
                    "execution_failed",
                    run_id=str(run_id),
                    test_case_id=str(test_case.id),
                    error=str(e),
                )

            await self.execution_repo.session.flush()

        run.status = RunStatus.SCORING
        await self.run_repo.session.flush()
        return run

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    )
    async def _call_target_agent(
        self, agent: TargetAgent, test_case: TestCase, run: Run
    ) -> dict[str, Any]:
        timeout = httpx.Timeout(agent.timeout_seconds, connect=5.0)
        
        # Get execution for this test case to get trace/span IDs
        execution = await self.execution_repo.get_by_run_and_test_case(run.id, test_case.id)
        
        headers = {
            "Content-Type": "application/json",
            **agent.auth_config.get("headers", {}),
        }
        
        # Add trace headers for distributed tracing
        if execution and execution.trace_id:
            headers["X-Trace-ID"] = execution.trace_id
        if execution and execution.span_id:
            headers["X-Span-ID"] = execution.span_id

        request_body = self._build_request(agent, test_case)

        if execution:
            execution.target_request = request_body
            await self.execution_repo.session.flush()

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.post(
                    agent.endpoint_url,
                    json=request_body,
                    headers=headers,
                )
                response.raise_for_status()
            except httpx.TimeoutException as e:
                raise TargetAgentTimeoutError(agent.endpoint_url, agent.timeout_seconds) from e
            except httpx.HTTPStatusError as e:
                raise TargetAgentUnavailableError(agent.endpoint_url, e.response.status_code) from e
            except httpx.RequestError as e:
                raise TargetAgentError(f"Request failed: {e}") from e

        return self._extract_response(agent, response.json())

    def _build_request(self, agent: TargetAgent, test_case: TestCase) -> dict[str, Any]:
        template = agent.request_template
        if not template:
            return {"input": test_case.input}

        request = copy.deepcopy(template)

        def replace_variables(obj: Any) -> Any:
            if isinstance(obj, str):
                return obj.replace("{input}", test_case.input).replace(
                    "{test_case_id}", test_case.test_case_id
                )
            if isinstance(obj, dict):
                return {k: replace_variables(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [replace_variables(item) for item in obj]
            return obj

        return replace_variables(request)

    def _extract_response(self, agent: TargetAgent, response: dict[str, Any]) -> dict[str, Any]:
        extraction = agent.response_extraction
        if not extraction:
            return response

        result = {}
        for key, path in extraction.items():
            value = response
            try:
                for path_part in path.split("."):
                    if isinstance(value, list):
                        index = int(path_part)
                        value = value[index]
                    else:
                        value = value[path_part]
                result[key] = value
            except (KeyError, IndexError, ValueError, TypeError):
                result[key] = None
        return result
