import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel
from fastapi import APIRouter, Depends


class VulnerabilitySeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class VulnerabilityCategory(str, Enum):
    PROMPT_INJECTION = "prompt_injection"
    DATA_LEAKAGE = "data_leakage"
    INSECURE_API_CALL = "insecure_api_call"
    SECRET_EXPOSURE = "secret_exposure"
    INSECURE_OUTPUT = "insecure_output"
    UNVALIDATED_INPUT = "unvalidated_input"
    LLM_JAILBREAK = "llm_jailbreak"


@dataclass
class Finding:
    severity: VulnerabilitySeverity
    category: VulnerabilityCategory
    description: str
    file_path: str
    line_number: int | None = None
    evidence: str | None = None
    recommendation: str = ""


@dataclass
class ScanReport:
    report_id: str
    project_path: str
    scan_type: str
    findings: list[Finding]
    summary: dict[str, int]
    timestamp: datetime
    scanner_version: str = "1.0.0"


class LLMVulnerabilityScanner:
    """Scans Python codebases for LLM-specific vulnerabilities."""

    def __init__(self, project_path: str = "."):
        self.project_path = project_path
        self.findings: list[Finding] = []

    def scan(self) -> ScanReport:
        """Scan the project for vulnerabilities."""
        self.findings = []
        self._scan_prompt_injection()
        self._scan_secret_exposure()
        self._scan_insecure_api_calls()
        self._scan_unvalidated_input()
        self._scan_data_leakage()

        summary = self._generate_summary()
        return ScanReport(
            report_id=str(uuid4()),
            project_path=self.project_path,
            scan_type="full",
            findings=self.findings,
            summary=summary,
            timestamp=datetime.now(),
        )

    def _scan_prompt_injection(self):
        """Scan for prompt injection vulnerabilities in Python files."""
        for py_file in self._find_python_files():
            content = self._read_file(py_file)
            lines = content.split("\n")

            for i, line in enumerate(lines):
                if "eval(" in line or "exec(" in line:
                    self.findings.append(Finding(
                        severity=VulnerabilitySeverity.HIGH,
                        category=VulnerabilityCategory.LLM_JAILBREAK,
                        description="Use of eval/exec can enable code injection",
                        file_path=py_file,
                        line_number=i + 1,
                        evidence=line.strip(),
                        recommendation="Replace eval/exec with safe alternatives",
                    ))

                if "prompt" in line.lower() and "system" in line.lower():
                    if "f" + '"' in line or "'" in line and "f" in line.split("=")[0] if "=" in line else False:
                        self.findings.append(Finding(
                            severity=VulnerabilitySeverity.CRITICAL,
                            category=VulnerabilityCategory.PROMPT_INJECTION,
                            description="Dynamic prompt construction may be vulnerable to injection",
                            file_path=py_file,
                            line_number=i + 1,
                            evidence=line.strip(),
                            recommendation="Use parameterized prompts or template validation",
                        ))

    def _scan_secret_exposure(self):
        """Scan for hardcoded secrets and API keys."""
        secret_patterns = [
            re.compile(r"(password|secret|api_key|apikey|token)\s*=\s*['\"][^'\"]{8,}['\"]", re.IGNORECASE),
            re.compile(r"sk-[a-zA-Z0-9]{20,}", re.IGNORECASE),
            re.compile(r"ghp_[a-zA-Z0-9]{36,}", re.IGNORECASE),
            re.compile(r"AIza[0-9A-Za-z_\-]{35}", re.IGNORECASE),
        ]

        for py_file in self._find_python_files():
            content = self._read_file(py_file)
            lines = content.split("\n")

            for i, line in enumerate(lines):
                for pattern in secret_patterns:
                    if pattern.search(line):
                        self.findings.append(Finding(
                            severity=VulnerabilitySeverity.CRITICAL,
                            category=VulnerabilityCategory.SECRET_EXPOSURE,
                            description="Hardcoded secret detected in source code",
                            file_path=py_file,
                            line_number=i + 1,
                            evidence=line.strip(),
                            recommendation="Move secrets to environment variables or a secrets manager",
                        ))

    def _scan_insecure_api_calls(self):
        """Scan for insecure API calls."""
        insecure_patterns = [
            re.compile(r"http://(?!localhost|127\.0\.0\.1)"),
            re.compile(r"urllib\.request\.urlopen"),
            re.compile(r"requests\.get\([^)]*verify\s*=\s*False"),
        ]

        for py_file in self._find_python_files():
            content = self._read_file(py_file)
            lines = content.split("\n")

            for i, line in enumerate(lines):
                for pattern in insecure_patterns:
                    if pattern.search(line):
                        self.findings.append(Finding(
                            severity=VulnerabilitySeverity.HIGH,
                            category=VulnerabilityCategory.INSECURE_API_CALL,
                            description="Insecure API call detected",
                            file_path=py_file,
                            line_number=i + 1,
                            evidence=line.strip(),
                            recommendation="Use HTTPS and verify SSL certificates",
                        ))

    def _scan_unvalidated_input(self):
        """Scan for unvalidated input handling."""
        for py_file in self._find_python_files():
            content = self._read_file(py_file)
            lines = content.split("\n")

            for i, line in enumerate(lines):
                if "request." in line and ("json()" in line or "args" in line or "params" in line):
                    if "validate" not in line.lower() and "pydantic" not in line.lower() and "BaseModel" not in content[max(0, content.find(line)-500):content.find(line)]:
                        self.findings.append(Finding(
                            severity=VulnerabilitySeverity.MEDIUM,
                            category=VulnerabilityCategory.UNVALIDATED_INPUT,
                            description="Request input may not be validated",
                            file_path=py_file,
                            line_number=i + 1,
                            evidence=line.strip(),
                            recommendation="Validate all incoming request data with Pydantic models",
                        ))

    def _scan_data_leakage(self):
        """Scan for potential data leakage patterns."""
        for py_file in self._find_python_files():
            content = self._read_file(py_file)
            lines = content.split("\n")

            for i, line in enumerate(lines):
                if "print(" in line and ("password" in line.lower() or "token" in line.lower() or "secret" in line.lower()):
                    self.findings.append(Finding(
                        severity=VulnerabilitySeverity.HIGH,
                        category=VulnerabilityCategory.DATA_LEAKAGE,
                        description="Potential data leakage via print statement",
                        file_path=py_file,
                        line_number=i + 1,
                        evidence=line.strip(),
                        recommendation="Remove sensitive data from print/logging statements",
                    ))

    def _generate_summary(self) -> dict[str, int]:
        summary = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for finding in self.findings:
            summary[finding.severity.value] += 1
        return summary

    def _find_python_files(self) -> list[str]:
        import os
        py_files = []
        for root, dirs, files in os.walk(self.project_path):
            for file in files:
                if file.endswith(".py"):
                    py_files.append(os.path.join(root, file))
        return py_files

    def _read_file(self, path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception:
            return ""


def run_security_scan(project_path: str = ".") -> ScanReport:
    """Convenience function to run a full security scan."""
    scanner = LLMVulnerabilityScanner(project_path)
    return scanner.scan()


class CodeScanResult(BaseModel):
    report_id: str
    project_path: str
    scan_type: str
    findings_count: int
    critical: int
    high: int
    medium: int
    low: int
    timestamp: datetime


router = APIRouter()


@router.get("/")
async def scan_project():
    report = run_security_scan(".")
    return {
        "report_id": report.report_id,
        "findings": len(report.findings),
        "summary": report.summary,
        "timestamp": report.timestamp.isoformat(),
    }


@router.get("/findings")
async def list_findings():
    report = run_security_scan(".")
    return {
        "findings": [
            {
                "severity": f.severity.value,
                "category": f.category.value,
                "description": f.description,
                "file_path": f.file_path,
                "line_number": f.line_number,
            }
            for f in report.findings
        ]
    }