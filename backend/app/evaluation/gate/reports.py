"""CI/CD Gate Reports - JUnit XML and JSON output for CI systems."""

import json
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.domain.enums import GateDecision, RunStatus, SeverityLevel, Verdict
from app.domain.value_objects import GateResult, RegressionFinding
from app.models.run import Run
from app.repositories.runs import ResultRepository, RunRepository
from app.repositories.baselines import RegressionRepository

logger = get_logger(__name__)


class GateReportGenerator:
    def __init__(
        self,
        run_repo: RunRepository,
        result_repo: ResultRepository,
        regression_repo: RegressionRepository,
    ):
        self.run_repo = run_repo
        self.result_repo = result_repo
        self.regression_repo = regression_repo

    async def generate_junit_xml(self, run_id: UUID, output_path: str | None = None) -> str:
        """Generate JUnit XML report for CI systems."""
        run = await self.run_repo.get(run_id)
        if not run:
            raise ValueError(f"Run not found: {run_id}")

        results = await self.result_repo.list_by_run(run_id)
        regressions = await self.regression_repo.list_by_run(run_id)

        testsuites = ET.Element("testsuites")
        testsuites.set("name", f"ARTEF Evaluation - {run.id}")
        testsuites.set("timestamp", run.created_at.isoformat() if run.created_at else datetime.utcnow().isoformat())
        
        testsuite = ET.SubElement(testsuites, "testsuite")
        testsuite.set("name", f"Run {str(run.id)[:8]}")
        testsuite.set("tests", str(len(results)))
        testsuite.set("failures", str(run.failed_count + run.regression_count))
        testsuite.set("errors", "0")
        testsuite.set("skipped", str(run.inconclusive_count))
        testsuite.set("time", str(run.total_latency_ms / 1000.0))

        properties = ET.SubElement(testsuite, "properties")
        for key, value in {
            "suite_id": str(run.suite_id),
            "agent_id": str(run.target_agent_id),
            "suite_version": str(run.suite_version),
            "framework_version": run.framework_version,
            "total_cost_usd": str(run.total_cost_usd),
            "gate_decision": run.status.value if run.status else "unknown",
        }.items():
            prop = ET.SubElement(properties, "property")
            prop.set("name", key)
            prop.set("value", value)

        for result in results:
            testcase = ET.SubElement(testsuite, "testcase")
            testcase.set("name", f"test_{str(result.test_case_id)[:8]}")
            testcase.set("classname", f"suite_{str(run.suite_id)[:8]}")
            testcase.set("time", str(result.execution_time_ms / 1000.0))

            if result.verdict == Verdict.FAIL:
                failure = ET.SubElement(testcase, "failure")
                failure.set("message", f"Test failed: {result.verdict.value}")
                failure.text = self._format_failure_details(result)
            elif result.verdict == Verdict.INCONCLUSIVE:
                skipped = ET.SubElement(testcase, "skipped")
                skipped.set("message", "Inconclusive result")

            # Add properties for the test case
            tc_properties = ET.SubElement(testcase, "properties")
            for key, value in {
                "confidence": str(result.confidence),
                "matcher": result.matcher_used.value if result.matcher_used else "unknown",
                "tokens_used": str(result.tokens_used),
                "estimated_cost": str(result.estimated_cost),
            }.items():
                prop = ET.SubElement(tc_properties, "property")
                prop.set("name", key)
                prop.set("value", value)

        # Add regression test cases
        for regression in regressions:
            testcase = ET.SubElement(testsuite, "testcase")
            testcase.set("name", f"regression_{str(regression.test_case_id)[:8]}")
            testcase.set("classname", f"regressions")
            testcase.set("time", "0")

            failure = ET.SubElement(testcase, "failure")
            failure.set("message", f"Regression: {regression.regression_type} ({regression.severity.value})")
            failure.text = (
                f"Previous: {regression.previous_verdict.value}\n"
                f"Current: {regression.current_verdict.value}\n"
                f"Type: {regression.regression_type}\n"
                f"Severity: {regression.severity.value}"
            )

        tree = ET.ElementTree(testsuites)
        ET.indent(tree, space="  ")

        if output_path:
            tree.write(output_path, encoding="utf-8", xml_declaration=True)
            logger.info("junit_xml_generated", run_id=str(run_id), path=output_path)
            return output_path
        
        from io import StringIO
        buffer = StringIO()
        tree.write(buffer, encoding="unicode", xml_declaration=True)
        return buffer.getvalue()

    async def generate_json_report(self, run_id: UUID, output_path: str | None = None) -> dict[str, Any]:
        """Generate JSON report for CI systems."""
        run = await self.run_repo.get(run_id)
        if not run:
            raise ValueError(f"Run not found: {run_id}")

        results = await self.result_repo.list_by_run(run_id)
        regressions = await self.regression_repo.list_by_run(run_id)

        report = {
            "metadata": {
                "run_id": str(run.id),
                "suite_id": str(run.suite_id),
                "suite_version": run.suite_version,
                "agent_id": str(run.target_agent_id),
                "framework_version": run.framework_version,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                "status": run.status.value if run.status else "unknown",
                "gate_decision": run.status.value if run.status else "unknown",
            },
            "summary": {
                "total_tests": run.total_tests,
                "passed": run.passed_count,
                "failed": run.failed_count,
                "inconclusive": run.inconclusive_count,
                "regressions": run.regression_count,
                "critical_findings": run.critical_count,
                "high_findings": run.high_count,
                "medium_findings": run.medium_count,
                "low_findings": run.low_count,
                "total_cost_usd": run.total_cost_usd,
                "total_latency_ms": run.total_latency_ms,
            },
            "test_results": [
                {
                    "test_case_id": str(r.test_case_id),
                    "verdict": r.verdict.value,
                    "confidence": r.confidence,
                    "matcher": r.matcher_used.value if r.matcher_used else None,
                    "execution_time_ms": r.execution_time_ms,
                    "tokens_used": r.tokens_used,
                    "estimated_cost": r.estimated_cost,
                    "errors": r.errors,
                }
                for r in results
            ],
            "regressions": [
                {
                    "test_case_id:": str(reg.test_case_id),
                    "previous_verdict": reg.previous_verdict.value,
                    "current_verdict": reg.current_verdict.value,
                    "regression_type": reg.regression_type,
                    "severity": reg.severity.value,
                    "evidence": reg.evidence,
                    "acknowledged": reg.acknowledged,
                }
                for reg in regressions
            ],
            "ci_gate": {
                "decision": self._get_gate_decision(run),
                "exit_code": self._get_exit_code(run),
                "blocked": self._is_blocked(run),
            },
        }

        if output_path:
            with open(output_path, "w") as f:
                json.dump(report, f, indent=2, default=str)
            logger.info("json_report_generated", run_id=str(run_id), path=output_path)

        return report

    def _format_failure_details(self, result) -> str:
        details = [
            f"Verdict: {result.verdict.value}",
            f"Confidence: {result.confidence:.2f}",
            f"Matcher: {result.matcher_used.value if result.matcher_used else 'unknown'}",
        ]
        if result.judge_output:
            details.append(f"Judge Verdict: {result.judge_output.get('verdict', 'unknown')}")
            details.append(f"Judge Rationale: {result.judge_output.get('rationale', 'none')}")
        if result.errors:
            details.append(f"Errors: {', '.join(result.errors)}")
        return "\n".join(details)

    def _get_gate_decision(self, run: Run) -> str:
        if run.status == RunStatus.COMPLETED:
            return GateDecision.PASS.value
        elif run.status == RunStatus.REVIEW_REQUIRED:
            return GateDecision.BLOCK.value
        elif run.status == RunStatus.FAILED:
            return GateDecision.FAIL.value
        return GateDecision.FAIL.value

    def _get_exit_code(self, run: Run) -> int:
        if run.status == RunStatus.COMPLETED:
            return 0
        elif run.status == RunStatus.REVIEW_REQUIRED:
            return 1
        elif run.status == RunStatus.FAILED:
            return 1
        return 2

    def _is_blocked(self, run: Run) -> bool:
        return run.status in (RunStatus.REVIEW_REQUIRED, RunStatus.FAILED)

    async def generate_ci_summary(self, run_id: UUID) -> dict[str, Any]:
        """Generate a summary suitable for CI badge/status."""
        run = await self.run_repo.get(run_id)
        if not run:
            return {"status": "error", "message": "Run not found"}

        decision = self._get_gate_decision(run)
        exit_code = self._get_exit_code(run)

        return {
            "run_id": str(run.id),
            "status": run.status.value if run.status else "unknown",
            "decision": decision,
            "exit_code": exit_code,
            "passed": run.passed_count,
            "failed": run.failed_count,
            "regressions": run.regression_count,
            "critical": run.critical_count,
            "high": run.high_count,
            "medium": run.medium_count,
            "low": run.low_count,
            "cost_usd": run.total_cost_usd,
        }


class CLIReporter:
    """CLI-friendly report generator for CI/CD integration."""

    def __init__(self, generator: GateReportGenerator):
        self.generator = generator

    async def run_and_report(self, run_id: UUID, output_dir: str = "reports") -> int:
        """Run evaluation and generate reports. Returns exit code."""
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Generate reports
        junit_path = Path(output_dir) / f"junit_{run_id}.xml"
        json_path = Path(output_dir) / f"report_{run_id}.json"

        await self.generator.generate_junit_xml(run_id, str(junit_path))
        await self.generator.generate_json_report(run_id, str(json_path))

        # Get CI summary
        summary = await self.generator.generate_ci_summary(run_id)
        exit_code = summary.get("exit_code", 2)

        # Print summary to stdout for CI logs
        print(f"ARTEF Evaluation Complete: {summary['run_id'][:8]}")
        print(f"Decision: {summary['decision']}")
        print(f"Tests: {summary['passed']} passed, {summary['failed']} failed, {summary.get('regressions', 0)} regressions")
        print(f"Critical: {summary['critical']}, High: {summary['high']}, Medium: {summary['medium']}, Low: {summary['low']}")
        print(f"Cost: ${summary['cost_usd']:.4f}")
        print(f"Reports: {junit_path}, {json_path}")

        return exit_code