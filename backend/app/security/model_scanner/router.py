from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_role
from app.core.exceptions import NotFoundError
from app.core.security import TokenData
from app.security.model_scanner.scanner import ModelScanner, ScanConfig

router = APIRouter()


class SecurityScanRequest(BaseModel):
    model_path: str
    model_id: str | None = None
    config: dict[str, Any] | None = None


class SecurityScanResponse(BaseModel):
    report_id: str
    model_path: str
    scan_status: str
    findings_count: int
    critical: int
    high: int
    medium: int
    low: int
    errors: list[str]
    scan_duration_ms: int


class ModelSecurityReport(BaseModel):
    report_id: str
    model_path: str
    scan_status: str
    findings: list[dict[str, Any]]
    timestamp: str


@router.post("/scan-model", response_model=SecurityScanResponse)
async def scan_model(
    request: SecurityScanRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer"])),
):
    """Scan a model for security vulnerabilities."""
    config = ScanConfig()
    if request.config:
        if "scan_pickles" in request.config:
            config.scan_pickles = request.config["scan_pickles"]
        if "scan_pytorch" in request.config:
            config.scan_pytorch = request.config["scan_pytorch"]
        if "scan_huggingface" in request.config:
            config.scan_huggingface = request.config["scan_huggingface"]
        if "max_file_size_mb" in request.config:
            config.max_file_size_mb = request.config["max_file_size_mb"]

    scanner = ModelScanner(config)
    report = await scanner.scan(request.model_path, request.model_id)

    return SecurityScanResponse(
        report_id=report.model_id,
        model_path=report.model_path,
        scan_status=report.scan_status,
        findings_count=len(report.findings),
        critical=sum(1 for f in report.findings if f.severity.value == "critical"),
        high=sum(1 for f in report.findings if f.severity.value == "high"),
        medium=sum(1 for f in report.findings if f.severity.value == "medium"),
        low=sum(1 for f in report.findings if f.severity.value == "low"),
        errors=report.errors,
        scan_duration_ms=report.scan_duration_ms,
    )


@router.get("/security-dashboard")
async def security_dashboard(db: AsyncSession = Depends(get_db)):
    """Get security dashboard data."""
    from app.monitoring import security_metrics, security_monitor

    return security_metrics.get_security_dashboard()


@router.post("/run-benchmark")
async def run_benchmark(
    benchmark_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer"])),
):
    """Run a benchmark evaluation."""
    from app.evaluation.benchmark import benchmark_runner, BenchmarkType

    try:
        result = await benchmark_runner.run_benchmark(BenchmarkType(benchmark_type))
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/benchmarks")
async def list_benchmarks(db: AsyncSession = Depends(get_db)):
    """List all available benchmarks."""
    from app.evaluation.benchmark import benchmark_runner

    return {
        "benchmarks": list(benchmark_runner._benchmarks.keys()),
        "adversarial_categories": benchmark_runner._benchmarks.keys(),
    }


@router.post("/code-scan")
async def scan_code(
    project_path: str = ".",
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_role(["admin"])),
):
    """Scan project code for LLM vulnerabilities."""
    from app.code_scanning import run_security_scan

    from app.code_scanning import run_security_scan

    report = run_security_scan(project_path)
    return {
        "report_id": report.report_id,
        "project_path": report.project_path,
        "findings": len(report.findings),
        "summary": report.summary,
        "timestamp": report.timestamp.isoformat(),
    }


@router.post("/ci-gate")
async def run_ci_gate(
    test_results: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_role(["admin"])),
):
    """Run CI/CD security gates."""
    from app.integrations import CICDPipeline

    pipeline = CICDPipeline()
    gate_results = await pipeline.run_security_gates(test_results)
    return {
        "gates": [g.to_dict() for g in gate_results],
        "all_passed": all(g.status.value == "success" for g in gate_results),
        "timestamp": datetime.now().isoformat(),
    }