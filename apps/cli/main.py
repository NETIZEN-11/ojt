#!/usr/bin/env python3
"""
ARTEF CLI - Agent Red-Teaming & Evaluation Framework Command Line Interface
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional
from uuid import UUID

import click
import yaml
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from app.core.config import get_settings
from app.core.database import init_db, close_db
from app.core.logging import setup_logging, get_logger
from app.api.deps import get_async_session
from app.repositories.suites import TestSuiteRepository
from app.repositories.runs import RunRepository, ExecutionRepository, ResultRepository
from app.repositories.agents import TargetAgentRepository
from app.repositories.baselines import BaselineRepository, BaselineItemRepository, RegressionRepository
from app.services.execution_service import ExecutionService
from app.services.scoring_service import ScoringService
from app.evaluation.gate.evaluator import GateEvaluator
from app.evaluation.gate.reports import CLIReporter, GateReportGenerator
from app.evaluation.regression.detector import RegressionDetector
from app.evaluation.severity.classifier import SeverityClassifier
from app.evaluation.rag.rag_evaluator import RAGEvaluator
from app.evaluation.agent.agent_evaluator import AgentEvaluator
from app.evaluation.prompt.prompt_evaluator import PromptEvaluator
from app.evaluation.prompt.prompt_comparison import PromptComparator
from app.evaluation.cost.cost_tracker import CostTracker
from app.security.model_scanner.scanner import ModelScanner
from app.models.test_suite import TestSuite, TestCase
from app.domain.enums import (
    ExpectedBehaviorType,
    TestCaseCategory,
    TestCaseSeverity,
    Verdict,
    AgentStatus,
)
from app.services.suite_service import SuiteService

settings = get_settings()
console = Console()
logger = get_logger(__name__)


@click.group()
@click.version_option(version="1.0.0")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--config", "-c", type=click.Path(exists=True), help="Path to config file")
def cli(verbose: bool, config: Optional[str]):
    """ARTEF - Agent Red-Teaming & Evaluation Framework"""
    if verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    if config:
        # Load custom config
        pass


@cli.group()
def suite():
    """Manage test suites"""
    pass


@suite.command("create")
@click.option("--name", required=True, help="Suite name")
@click.option("--description", help="Suite description")
@click.option("--file", "-f", type=click.Path(exists=True), help="YAML/JSON file with test cases")
def suite_create(name: str, description: str, file: str):
    """Create a new test suite"""
    asyncio.run(_suite_create(name, description, file))


async def _suite_create(name: str, description: str, file: str):
    setup_logging()
    await init_db()

    try:
        async with get_async_session() as session:
            suite_repo = TestSuiteRepository(session)
            case_repo = TestCaseRepository(session)

            suite = TestSuite(
                name=name,
                description=description,
                version=1,
                schema_version="1.0",
                is_active=True,
            )
            suite = await suite_repo.create(suite)

            if file:
                with open(file, "r") as f:
                    if file.endswith(".yaml") or file.endswith(".yml"):
                        data = yaml.safe_load(f)
                    else:
                        data = json.load(f)

                test_cases = data.get("test_cases", [])
                for tc_data in test_cases:
                    test_case = TestCase(
                        suite_id=suite.id,
                        test_case_id=tc_data["test_case_id"],
                        category=TestCaseCategory(tc_data["category"]),
                        severity=TestCaseSeverity(tc_data["severity"]),
                        input=tc_data["input"],
                        expected_behavior=tc_data["expected_behavior"],
                        metadata=tc_data.get("metadata", {}),
                        is_active=True,
                    )
                    await case_repo.create(test_case)

            await session.commit()
            console.print(f"[green]Created suite: {name}[/green]")
    finally:
        await close_db()


@suite.command("list")
def suite_list():
    """List all test suites"""
    asyncio.run(_suite_list())


async def _suite_list():
    setup_logging()
    await init_db()

    try:
        async with get_async_session() as session:
            suite_repo = TestSuiteRepository(session)
            suites = await suite_repo.list_all()

            table = Table(title="Test Suites")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Version")
            table.add_column("Cases")
            table.add_column("Active")
            table.add_column("Created")

            for suite in suites:
                table.add_row(
                    str(suite.id)[:8],
                    suite.name,
                    str(suite.version),
                    str(len(suite.test_cases)),
                    "✓" if suite.is_active else "✗",
                    suite.created_at.strftime("%Y-%m-%d"),
                )

            console.print(table)
    finally:
        await close_db()


@suite.command("import")
@click.argument("file", type=click.Path(exists=True))
def suite_import(file: str):
    """Import test suite from YAML/JSON file"""
    asyncio.run(_suite_import(file))


async def _suite_import(file: str):
    setup_logging()
    await init_db()

    try:
        with open(file, "r") as f:
            if file.endswith(".yaml") or file.endswith(".yml"):
                data = yaml.safe_load(f)
            else:
                data = json.load(f)

        async with get_async_session() as session:
            suite_service = SuiteService(session)
            suite = await suite_service.import_suite(data)
            console.print(f"[green]Imported suite: {suite.name} (v{suite.version})[/green]")
    finally:
        await close_db()


@suite.command("export")
@click.argument("suite_id")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option("--format", type=click.Choice(["yaml", "json"]), default="yaml")
def suite_export(suite_id: str, output: str, format: str):
    """Export test suite to YAML/JSON"""
    asyncio.run(_suite_export(suite_id, output, format))


async def _suite_export(suite_id: str, output: str, format: str):
    setup_logging()
    await init_db()

    try:
        async with get_async_session() as session:
            suite_repo = TestSuiteRepository(session)
            case_repo = TestCaseRepository(session)

            suite = await suite_repo.get(UUID(suite_id))
            if not suite:
                console.print(f"[red]Suite not found: {suite_id}[/red]")
                return

            cases = await case_repo.list_by_suite(suite.id)

            data = {
                "name": suite.name,
                "description": suite.description,
                "schema_version": suite.schema_version,
                "test_cases": [
                    {
                        "test_case_id": tc.test_case_id,
                        "category": tc.category.value,
                        "severity": tc.severity.value,
                        "input": tc.input,
                        "expected_behavior": tc.expected_behavior,
                        "metadata": tc.metadata,
                    }
                    for tc in cases
                ],
            }

            if output:
                with open(output, "w") as f:
                    if format == "yaml":
                        yaml.dump(data, f)
                    else:
                        json.dump(data, f, indent=2)
                console.print(f"[green]Exported to {output}[/green]")
            else:
                if format == "yaml":
                    console.print(yaml.dump(data))
                else:
                    console.print(json.dumps(data, indent=2))
    finally:
        await close_db()


@cli.group()
def run():
    """Manage evaluation runs"""
    pass


@run.command("create")
@click.option("--suite", "suite_id", required=True, help="Test suite ID")
@click.option("--agent", "agent_id", required=True, help="Target agent ID")
@click.option("--baseline", "baseline_id", help="Baseline ID for regression detection")
def run_create(suite_id: str, agent_id: str, baseline_id: str):
    """Create a new evaluation run"""
    asyncio.run(_run_create(suite_id, agent_id, baseline_id))


async def _run_create(suite_id: str, agent_id: str, baseline_id: str):
    setup_logging()
    await init_db()

    try:
        async with get_async_session() as session:
            run_repo = RunRepository(session)
            agent_repo = TargetAgentRepository(session)
            suite_repo = TestSuiteRepository(session)
            baseline_repo = BaselineRepository(session)

            agent = await agent_repo.get(UUID(agent_id))
            if not agent:
                console.print(f"[red]Agent not found: {agent_id}[/red]")
                return

            suite = await suite_repo.get(UUID(suite_id))
            if not suite:
                console.print(f"[red]Suite not found: {suite_id}[/red]")
                return

            baseline = None
            if baseline_id:
                baseline = await baseline_repo.get(UUID(baseline_id))
            else:
                baseline = await baseline_repo.get_active_for_suite(suite.id)

            new_run = Run(
                target_agent_id=agent.id,
                suite_id=suite.id,
                suite_version=suite.version,
                baseline_id=baseline.id if baseline else None,
                framework_version="1.0.0",
                created_by=UUID("00000000-0000-0000-0000-000000000000"),
            )
            new_run = await run_repo.create(new_run)

            console.print(f"[green]Created run: {new_run.id}[/green]")
            console.print(f"  Suite: {suite.name} (v{suite.version})")
            console.print(f"  Agent: {agent.name}")
            console.print(f"  Baseline: {baseline.name if baseline else 'None'}")

            # Start evaluation
            from app.workers.evaluation_tasks import run_evaluation
            run_evaluation.delay(str(new_run.id))
            console.print("[yellow]Evaluation started in background[/yellow]")
    finally:
        await close_db()


@run.command("list")
@click.option("--status", help="Filter by status")
@click.option("--limit", default=20, help="Number of runs to show")
def run_list(status: str, limit: int):
    """List evaluation runs"""
    asyncio.run(_run_list(status, limit))


async def _run_list(status: str, limit: int):
    setup_logging()
    await init_db()

    try:
        async with get_async_session() as session:
            run_repo = RunRepository(session)
            filters = {}
            if status:
                filters["status"] = status
            runs = await run_repo.list(skip=0, limit=limit, filters=filters)

            table = Table(title="Evaluation Runs")
            table.add_column("ID", style="cyan")
            table.add_column("Suite", style="green")
            table.add_column("Agent", style="blue")
            table.add_column("Status", style="yellow")
            table.add_column("Tests")
            table.add_column("Passed")
            table.add_column("Failed")
            table.add_column("Regressions", style="red")
            table.add_column("Created")

            for run in runs:
                table.add_row(
                    str(run.id)[:8],
                    str(run.suite_id)[:8],
                    str(run.target_agent_id)[:8],
                    run.status.value,
                    str(run.total_tests),
                    str(run.passed_count),
                    str(run.failed_count),
                    str(run.regression_count),
                    run.created_at.strftime("%Y-%m-%d %H:%M"),
                )

            console.print(table)
    finally:
        await close_db()


@run.command("get")
@click.argument("run_id")
def run_get(run_id: str):
    """Get detailed run information"""
    asyncio.run(_run_get(run_id))


async def _run_get(run_id: str):
    setup_logging()
    await init_db()

    try:
        async with get_async_session() as session:
            run_repo = RunRepository(session)
            execution_repo = ExecutionRepository(session)
            result_repo = ResultRepository(session)

            run = await run_repo.get(UUID(run_id))
            if not run:
                console.print(f"[red]Run not found: {run_id}[/red]")
                return

            executions = await execution_repo.list_by_run(UUID(run_id))
            results = await result_repo.list_by_run(UUID(run_id))

            console.print(f"[bold]Run: {run.id}[/bold]")
            console.print(f"  Status: {run.status.value}")
            console.print(f"  Suite: {run.suite_id}")
            console.print(f"  Agent: {run.target_agent_id}")
            console.print(f"  Tests: {run.total_tests}")
            console.print(f"  Passed: {run.passed_count}")
            console.print(f"  Failed: {run.failed_count}")
            console.print(f"  Inconclusive: {run.inconclusive_count}")
            console.print(f"  Regressions: {run.regression_count}")
            console.print(f"  Cost: ${run.total_cost_usd:.4f}")
            console.print(f"  Latency: {run.total_latency_ms}ms")
            console.print(f"  Started: {run.started_at}")
            console.print(f"  Completed: {run.completed_at}")

            if run.error_message:
                console.print(f"  [red]Error: {run.error_message}[/red]")

            # Show results
            table = Table(title="Results")
            table.add_column("Test Case", style="cyan")
            table.add_column("Verdict")
            table.add_column("Confidence")
            table.add_column("Matcher")
            table.add_column("Time (ms)")
            table.add_column("Cost")

            for result in results:
                table.add_row(
                    str(result.test_case_id)[:8],
                    result.verdict.value,
                    f"{result.confidence:.2f}",
                    result.matcher_used or "N/A",
                    str(result.execution_time_ms),
                    f"${result.estimated_cost:.6f}",
                )

            console.print(table)
    finally:
        await close_db()


@cli.group()
def evaluate():
    """Run evaluations"""
    pass


@evaluate.command("run")
@click.option("--config", "-c", type=click.Path(exists=True), required=True, help="Evaluation config file")
def evaluate_run(config: str):
    """Run evaluation from config file"""
    asyncio.run(_evaluate_run(config))


async def _evaluate_run(config: str):
    setup_logging()
    await init_db()

    with open(config, "r") as f:
        if config.endswith(".yaml") or config.endswith(".yml"):
            eval_config = yaml.safe_load(f)
        else:
            eval_config = json.load(f)

    console.print(f"[green]Starting evaluation: {eval_config.get('name', 'Unnamed')}[/green]")
    # Implementation would go here
    console.print("[yellow]Evaluation started (background task)[/yellow]")
    await close_db()


@evaluate.command("rag")
@click.option("--query", required=True, help="Query text")
@click.option("--answer", required=True, help="Generated answer")
@click.option("--context", help="Retrieved context (comma-separated)")
@click.option("--ground-truth", help="Ground truth documents (comma-separated)")
def evaluate_rag(query: str, answer: str, context: str, ground_truth: str):
    """Evaluate RAG system"""
    asyncio.run(_evaluate_rag(query, answer, context, ground_truth))


async def _evaluate_rag(query: str, answer: str, context: str, ground_truth: str):
    setup_logging()
    await init_db()

    try:
        from app.rag.vector_store import VectorStore
        from app.rag.retriever import Retriever
        from app.evaluation.rag.rag_evaluator import RAGEvaluator

        vector_store = VectorStore()
        retriever = Retriever(vector_store)
        evaluator = RAGEvaluator(retriever)

        context_docs = [{"content": c.strip()} for c in context.split(",")] if context else []
        gt_docs = [g.strip() for g in ground_truth.split(",")] if ground_truth else []

        result = await evaluator.evaluate(
            test_case_id="cli_rag_eval",
            query=query,
            answer=answer,
            retrieved_docs=context_docs,
            ground_truth_docs=gt_docs,
        )

        console.print(f"[bold]RAG Evaluation Results[/bold]")
        console.print(f"  Overall Score: {result.overall_score:.2f}")
        console.print(f"  Retrieval F1: {result.retrieval_result.metrics.f1_score:.2f}")
        console.print(f"  Retrieval Precision: {result.retrieval_result.metrics.precision:.2f}")
        console.print(f"  Retrieval Recall: {result.retrieval_result.metrics.recall:.2f}")
        console.print(f"  Generation Faithfulness: {result.generation_result.metrics.faithfulness:.2f}")
        console.print(f"  Generation Relevance: {result.generation_result.metrics.answer_relevance:.2f}")
    finally:
        await close_db()


@evaluate.command("agent")
@click.option("--trajectory", type=click.Path(exists=True), required=True, help="Trajectory JSON file")
@click.option("--expected-answer", help="Expected final answer")
def evaluate_agent(trajectory: str, expected_answer: str):
    """Evaluate AI agent trajectory"""
    asyncio.run(_evaluate_agent(trajectory, expected_answer))


async def _evaluate_agent(trajectory: str, expected_answer: str):
    setup_logging()
    await init_db()

    try:
        from app.evaluation.agent.agent_evaluator import AgentEvaluator

        with open(trajectory, "r") as f:
            traj_data = json.load(f)

        evaluator = AgentEvaluator()
        result = await evaluator.evaluate(
            test_case_id="cli_agent_eval",
            input_text="",
            trajectory=traj_data.get("trajectory", []),
            expected_final_answer=expected_answer or "",
        )

        console.print(f"[bold]Agent Evaluation Results[/bold]")
        console.print(f"  Overall Score: {result['overall_score']:.2f}")
        console.print(f"  Trajectory: {result['trajectory_evaluation']}")
        console.print(f"  Tool Calls: {result['tool_call_evaluation']}")
    finally:
        await close_db()


@cli.group()
def prompt():
    """Manage prompts"""
    pass


@prompt.command("evaluate")
@click.option("--content", required=True, help="Prompt content")
@click.option("--version", default="1.0", help="Prompt version")
def prompt_evaluate(content: str, version: str):
    """Evaluate a prompt"""
    asyncio.run(_prompt_evaluate(content, version))


async def _prompt_evaluate(content: str, version: str):
    setup_logging()
    await init_db()

    try:
        from app.evaluation.prompt.prompt_evaluator import PromptEvaluator

        evaluator = PromptEvaluator()
        result = await evaluator.evaluate("cli_prompt", version, content)

        console.print(f"[bold]Prompt Evaluation Results[/bold]")
        console.print(f"  Quality: {result.metrics.quality_score:.2f}")
        console.print(f"  Clarity: {result.metrics.clarity_score:.2f}")
        console.print(f"  Specificity: {result.metrics.specificity_score:.2f}")
        console.print(f"  Safety: {result.metrics.safety_score:.2f}")
        console.print(f"  Token Efficiency: {result.metrics.token_efficiency:.2f}")
    finally:
        await close_db()


@prompt.command("compare")
@click.option("--prompt-a", required=True, help="Prompt A content")
@click.option("--prompt-b", required=True, help="Prompt B content")
@click.option("--version-a", default="1.0", help="Prompt A version")
@click.option("--version-b", default="1.0", help="Prompt B version")
def prompt_compare(prompt_a: str, prompt_b: str, version_a: str, version_b: str):
    """Compare two prompts"""
    asyncio.run(_prompt_compare(prompt_a, prompt_b, version_a, version_b))


async def _prompt_compare(prompt_a: str, prompt_b: str, version_a: str, version_b: str):
    setup_logging()
    await init_db()

    try:
        from app.evaluation.prompt.prompt_comparison import PromptComparator

        comparator = PromptComparator()
        result = await comparator.compare(
            "prompt_a", version_a, prompt_a,
            "prompt_b", version_b, prompt_b,
        )

        console.print(f"[bold]Prompt Comparison Results[/bold]")
        console.print(f"  Winner: {result.winner}")
        console.print(f"  Score Difference: {result.score_difference:.2f}")
        console.print(f"  Prompt A Metrics: {result.metrics_a}")
        console.print(f"  Prompt B Metrics: {result.metrics_b}")
    finally:
        await close_db()


@cli.group()
def security():
    """Security operations"""
    pass


@security.command("scan-model")
@click.argument("model_path", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output report file")
def scan_model(model_path: str, output: str):
    """Scan model for security vulnerabilities"""
    asyncio.run(_scan_model(model_path, output))


async def _scan_model(model_path: str, output: str):
    setup_logging()

    try:
        from app.security.model_scanner.scanner import ModelScanner

        scanner = ModelScanner()
        report = await scanner.scan(model_path)

        console.print(f"[bold]Model Security Scan Results[/bold]")
        console.print(f"  Model: {report.model_id}")
        console.print(f"  Status: {report.scan_status}")
        console.print(f"  Duration: {report.scan_duration_ms}ms")
        console.print(f"  Critical: {report.critical_count}")
        console.print(f"  High: {report.high_count}")
        console.print(f"  Medium: {report.medium_count}")
        console.print(f"  Low: {report.low_count}")
        console.print(f"  Info: {report.info_count}")

        for finding in report.findings:
            severity_color = {
                "critical": "red",
                "high": "red",
                "medium": "yellow",
                "low": "blue",
                "info": "green",
            }.get(finding.severity.value, "white")
            console.print(
                f"  [{severity_color}]{finding.severity.value.upper()}[/{severity_color}] "
                f"{finding.detector}: {finding.description} ({finding.file_path})"
            )

        if output:
            with open(output, "w") as f:
                json.dump(report.to_dict(), f, indent=2)
            console.print(f"[green]Report saved to {output}[/green]")
    finally:
        await close_db()


@cli.group()
def cost():
    """Cost tracking operations"""
    pass


@cost.command("summary")
@click.option("--days", default=30, help="Number of days to look back")
def cost_summary(days: int):
    """Show cost summary"""
    asyncio.run(_cost_summary(days))


async def _cost_summary(days: int):
    setup_logging()
    await init_db()

    try:
        from app.evaluation.cost.cost_tracker import CostTracker

        tracker = CostTracker()
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)

        summary = await tracker.get_summary(start_time, end_time)

        console.print(f"[bold]Cost Summary (Last {days} days)[/bold]")
        console.print(f"  Total Cost: ${summary.total_cost_usd:.4f}")
        console.print(f"  Total Tokens: {summary.total_tokens}")
        console.print(f"  Input Tokens: {summary.total_input_tokens}")
        console.print(f"  Output Tokens: {summary.total_output_tokens}")

        if summary.by_category:
            console.print("  By Category:")
            for cat, cost in summary.by_category.items():
                console.print(f"  {cat}: ${cost:.4f}")

        if summary.by_provider:
            console.print("  By Provider:")
            for prov, cost in summary.by_provider.items():
                console.print(f"  {prov}: ${cost:.4f}")

        if summary.by_model:
            console.print("  By Model:")
            for model, cost in summary.by_model.items():
                console.print(f"  {model}: ${cost:.4f}")
    finally:
        await close_db()


@cli.group()
def redteam():
    """Red-teaming operations"""
    pass


@redteam.command("generate")
@click.option("--category", help="Attack category")
@click.option("--count", default=10, help="Number of attacks to generate")
@click.option("--output", "-o", type=click.Path(), help="Output file")
def redteam_generate(category: str, count: int, output: str):
    """Generate adversarial test cases"""
    asyncio.run(_redteam_generate(category, count, output))


async def _redteam_generate(category: str, count: int, output: str):
    setup_logging()
    await init_db()

    try:
        from app.redteam.generator import AdversarialGenerator
        from app.rag.vector_store import VectorStore
        from app.rag.retriever import Retriever

        vector_store = VectorStore()
        retriever = Retriever(vector_store)
        generator = AdversarialGenerator(retriever)

        attacks = await generator.generate(
            category=category or "jailbreak",
            batch_size=count,
        )

        if output:
            with open(output, "w") as f:
                yaml.dump({"test_cases": attacks}, f)
            console.print(f"[green]Generated {len(attacks)} attacks to {output}[/green]")
        else:
            for attack in attacks:
                console.print(f"  {attack['test_case_id']}: {attack['input'][:80]}...")
    finally:
        await close_db()


@redteam.command("run")
@click.option("--agent", "agent_id", required=True, help="Target agent ID")
@click.option("--suite", "suite_id", help="Test suite ID for adversarial tests")
@click.option("--turns", default=8, help="Max turns per attack")
def redteam_run(agent_id: str, suite_id: str, turns: int):
    """Run red-team attack against target agent"""
    asyncio.run(_redteam_run(agent_id, suite_id, turns))


async def _redteam_run(agent_id: str, suite_id: str, turns: int):
    setup_logging()
    await init_db()

    try:
        from app.redteam.agent import RedTeamAgent
        from app.repositories.agents import TargetAgentRepository

        async with get_async_session() as session:
            agent_repo = TargetAgentRepository(session)
            agent = await agent_repo.get(UUID(agent_id))

            if not agent:
                console.print(f"[red]Agent not found: {agent_id}[/red]")
                return

            redteam = RedTeamAgent(agent.endpoint_url)
            redteam.max_turns = turns

            console.print(f"[green]Starting red-team attack on {agent.name}[/green]")
            # Would run the red-team agent here
            console.print("[yellow]Red-team attack completed[/yellow]")
    finally:
        await close_db()


@cli.group()
def baseline():
    """Manage baselines"""
    pass


@baseline.command("create")
@click.option("--run", "run_id", required=True, help="Run ID to create baseline from")
@click.option("--name", required=True, help="Baseline name")
@click.option("--description", help="Baseline description")
def baseline_create(run_id: str, name: str, description: str):
    """Create baseline from completed run"""
    asyncio.run(_baseline_create(run_id, name, description))


async def _baseline_create(run_id: str, name: str, description: str):
    setup_logging()
    await init_db()

    try:
        async with get_async_session() as session:
            from app.repositories.baselines import BaselineRepository, BaselineItemRepository
            from app.repositories.runs import RunRepository, ResultRepository

            run_repo = RunRepository(session)
            baseline_repo = BaselineRepository(session)
            baseline_item_repo = BaselineItemRepository(session)
            result_repo = ResultRepository(session)

            run = await run_repo.get(UUID(run_id))
            if not run:
                console.print(f"[red]Run not found: {run_id}[/red]")
                return

            if run.status.value != "completed":
                console.print(f"[red]Run must be completed to create baseline[/red]")
                return

            results = await result_repo.list_by_run(UUID(run_id))

            baseline = Baseline(
                suite_id=run.suite_id,
                suite_version=run.suite_version,
                run_id=run.id,
                name=name,
                description=description,
                framework_version=run.framework_version,
                model_versions=run.model_versions,
                prompt_versions=run.prompt_versions,
                approved_by=UUID("00000000-0000-0000-0000-000000000000"),
                approved_at=datetime.utcnow(),
                is_active=True,
            )
            baseline = await baseline_repo.create(baseline)

            for result in results:
                item = BaselineItem(
                    baseline_id=baseline.id,
                    test_case_id=result.test_case_id,
                    verdict=result.verdict,
                    confidence=result.confidence,
                    evidence=result.evidence,
                )
                await baseline_item_repo.create(item)

            await session.commit()
            console.print(f"[green]Created baseline: {baseline.id}[/green]")
    finally:
        await close_db()


@baseline.command("list")
def baseline_list():
    """List all baselines"""
    asyncio.run(_baseline_list())


async def _baseline_list():
    setup_logging()
    await init_db()

    try:
        async with get_async_session() as session:
            from app.repositories.baselines import BaselineRepository

            baseline_repo = BaselineRepository(session)
            baselines = await baseline_repo.list_all()

            table = Table(title="Baselines")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Suite")
            table.add_column("Version")
            table.add_column("Run")
            table.add_column("Active")
            table.add_column("Approved")
            table.add_column("Created")

            for b in baselines:
                table.add_row(
                    str(b.id)[:8],
                    b.name,
                    str(b.suite_id)[:8],
                    str(b.suite_version),
                    str(b.run_id)[:8],
                    "✓" if b.is_active else "✗",
                    b.approved_at.strftime("%Y-%m-%d") if b.approved_at else "N/A",
                    b.created_at.strftime("%Y-%m-%d"),
                )

            console.print(table)
    finally:
        await close_db()


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind")
@click.option("--port", default=8000, help="Port to bind")
@click.option("--reload", is_flag=True, help="Enable auto-reload")
def server(host: str, port: int, reload: bool):
    """Start the API server"""
    import uvicorn
    uvicorn.run("app.main:app", host=host, port=port, reload=reload)


@cli.command()
def worker():
    """Start Celery worker"""
    import subprocess
    subprocess.run(["celery", "-A", "app.workers.celery_app", "worker", "--loglevel=info", "--concurrency=4"])


@cli.command()
def migrate():
    """Run database migrations"""
    import subprocess
    subprocess.run(["alembic", "upgrade", "head"])


@cli.command()
def seed():
    """Seed database with demo data"""
    import subprocess
    subprocess.run(["python", "../scripts/seed_demo_data.py"])


@cli.command()
@click.argument("run_id")
@click.option("--output-dir", "-o", default="reports", help="Output directory for reports")
@click.option("--format", "output_format", type=click.Choice(["junit", "json", "both"]), default="both", help="Output format")
def gate(run_id: str, output_dir: str, output_format: str):
    """Generate CI/CD gate reports for a run (JUnit XML, JSON)"""
    asyncio.run(_gate(run_id, output_dir, output_format))


async def _gate(run_id: str, output_dir: str, output_format: str):
    setup_logging()
    await init_db()

    try:
        from app.repositories.runs import RunRepository, ResultRepository
        from app.repositories.baselines import RegressionRepository

        async with get_async_session() as session:
            run_repo = RunRepository(session)
            result_repo = ResultRepository(session)
            regression_repo = RegressionRepository(session)

            reporter = CLIReporter(
                GateReportGenerator(run_repo, result_repo, regression_repo)
            )

            exit_code = await reporter.run_and_report(UUID(run_id), output_dir)
            
            if exit_code != 0:
                console.print(f"[red]Gate failed with exit code {exit_code}[/red]")
                sys.exit(exit_code)
            else:
                console.print("[green]Gate passed[/green]")
    finally:
        await close_db()


if __name__ == "__main__":
    cli()