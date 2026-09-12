import json
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel
from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class CIStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PENDING = "pending"
    ERROR = "error"


class SecurityGateResult:
    def __init__(
        self,
        gate_name: str,
        status: CIStatus,
        score: float,
        findings: list[dict[str, Any]],
        threshold: float = 0.0,
    ):
        self.gate_name = gate_name
        self.status = status
        self.score = score
        self.findings = findings
        self.threshold = threshold
        self.timestamp = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate_name": self.gate_name,
            "status": self.status.value,
            "score": self.score,
            "threshold": self.threshold,
            "findings": self.findings,
            "timestamp": self.timestamp.isoformat(),
            "passed": self.status == CIStatus.SUCCESS,
        }


class CICDPipeline:
    """CI/CD pipeline integration for security gates."""

    def __init__(self):
        self.gates = {
            "prompt_injection": {"enabled": True, "threshold": 0.0},
            "data_leakage": {"enabled": True, "threshold": 0.0},
            "jailbreak": {"enabled": True, "threshold": 0.0},
            "pii_detection": {"enabled": True, "threshold": 0.0},
            "toxic_content": {"enabled": True, "threshold": 0.0},
            "model_security": {"enabled": True, "threshold": 0.0},
        }

    async def run_security_gates(self, test_results: dict[str, Any]) -> list[SecurityGateResult]:
        """Run all security gates against test results."""
        results = []
        for gate_name, config in self.gates.items():
            if not config["enabled"]:
                continue

            findings = test_results.get(gate_name, {}).get("findings", [])
            score = self._calculate_score(gate_name, findings)

            status = CIStatus.SUCCESS if score >= config["threshold"] else CIStatus.FAILURE
            result = SecurityGateResult(
                gate_name=gate_name,
                status=status,
                score=score,
                findings=findings,
                threshold=config["threshold"],
            )
            results.append(result)

            logger.info(
                "security_gate_result",
                gate=gate_name,
                status=status.value,
                score=score,
            )

        return results

    def _calculate_score(self, gate_name: str, findings: list) -> float:
        """Calculate security gate score."""
        if not findings:
            return 1.0

        severity_scores = {"critical": 0.0, "high": 0.25, "medium": 0.5, "low": 0.75}
        total = len(findings)
        passed = sum(1 for f in findings if f.get("severity") in ("low", "info"))
        return passed / total if total > 0 else 0.0

    def get_pipeline_config(self) -> dict[str, Any]:
        """Get the CI/CD pipeline configuration."""
        return {
            "gates": {k: v for k, v in self.gates.items()},
            "settings": settings,
            "version": "1.0.0",
            "updated_at": datetime.now().isoformat(),
        }


class GitHubIntegration:
    """GitHub integration for PR security checks."""

    def __init__(self):
        self.pipeline = CICDPipeline()

    async def check_pr(self, pr_data: dict[str, Any]) -> dict[str, Any]:
        """Check a pull request for security issues."""
        result = {
            "pr_number": pr_data.get("pr_number"),
            "repository": pr_data.get("repository"),
            "timestamp": datetime.now().isoformat(),
            "checks": [],
        }

        # Run security gates
        test_results = pr_data.get("test_results", {})
        gate_results = await self.pipeline.run_security_gates(test_results)

        for gate in gate_results:
            result["checks"].append(gate.to_dict())

        # Determine overall status
        all_passed = all(g.status == CIStatus.SUCCESS for g in gate_results)
        result["status"] = "pass" if all_passed else "fail"
        result["message"] = "All security gates passed" if all_passed else "Security gates failed"

        return result

    def generate_pr_comment(self, result: dict[str, Any]) -> str:
        """Generate a PR comment with security results."""
        lines = [
            "## 🔒 Security Scan Results",
            f"**Status:** {'✅ Pass' if result['status'] == 'pass' else '❌ Fail'}",
            "",
        ]
        for check in result.get("checks", []):
            status = "✅" if check["passed"] else "❌"
            lines.append(f"{status} **{check['gate_name']}**: {check['score']:.2f}")
            for finding in check.get("findings", []):
                lines.append(f"  - {finding.get('description', 'Unknown')}")
        lines.append("")
        lines.append("---")
        return "\n".join(lines)


class WebhookHandler:
    """Handle incoming webhooks from CI/CD platforms."""

    def __init__(self):
        self.github = GitHubIntegration()

    async def handle_github_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Handle GitHub webhook events."""
        event = payload.get("action", "")
        repository = payload.get("repository", {}).get("full_name", "")

        if event in ("opened", "synchronize"):
            pr_number = payload.get("pull_request", {}).get("number")
            pr_data = {
                "pr_number": pr_number,
                "repository": repository,
                "test_results": payload.get("test_results", {}),
            }
            return await self.github.check_pr(pr_data)

        return {"status": "ignored", "event": event}


class IntegrationConfig(BaseModel):
    """Configuration for platform integrations."""
    github_enabled: bool = True
    gitlab_enabled: bool = False
    slack_webhook_url: str = ""
    notify_on_failure: bool = True
    notify_channel: str = "security-alerts"


from pydantic import BaseModel