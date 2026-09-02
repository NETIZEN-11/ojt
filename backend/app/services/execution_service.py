import copy
from datetime import datetime
from typing import Any
from uuid import UUID

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
from app.models.run import Execution, Run
from app.models.target_agent import TargetAgent
from app.models.test_suite import TestCase
from app.repositories.agents import TargetAgentRepository
from app.repositories.runs import ExecutionRepository, ResultRepository, RunRepository
from app.repositories.suites import TestCaseRepository

settings = get_settings()
logger = get_logger(__name__)


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

        for test_case in test_cases:
            execution = Execution(
                run_id=run.id,
                test_case_id=test_case.id,
                status=ExecutionStatus.RUNNING,
                started_at=datetime.utcnow(),
            )
            execution = await self.execution_repo.create(execution)

            try:
                response = await self._call_target_agent(agent, test_case, run)
                execution.target_response = response
                execution.status = ExecutionStatus.COMPLETED
                execution.completed_at = datetime.utcnow()
                elapsed = execution.completed_at - execution.started_at
                execution.latency_ms = int(elapsed.total_seconds() * 1000)
            except Exception as e:
                execution.status = ExecutionStatus.FAILED
                execution.completed_at = datetime.utcnow()
                execution.error = str(e)
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
        headers = {
            "Content-Type": "application/json",
            **agent.auth_config.get("headers", {}),
        }

        request_body = self._build_request(agent, test_case)

        execution = await self.execution_repo.get_by_run_and_test_case(run.id, test_case.id)
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
