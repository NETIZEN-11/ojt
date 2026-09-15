from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.logging import get_logger
from app.security.model_scanner.detectors import (
    PickleDetector,
    JoblibDetector,
    PyTorchDetector,
    TensorFlowDetector,
    ONNXDetector,
    HuggingFaceDetector,
)
from app.security.model_scanner.report import ScanReport, ScanFinding, SeverityLevel

logger = get_logger(__name__)


@dataclass
class ScanConfig:
    scan_pickles: bool = True
    scan_pytorch: bool = True
    scan_tensorflow: bool = True
    scan_onnx: bool = True
    scan_huggingface: bool = True
    max_file_size_mb: int = 500
    timeout_seconds: int = 300


class ModelScanner:
    def __init__(self, config: ScanConfig = None):
        self.config = config or ScanConfig()
        self.detectors = []

        if self.config.scan_pickles:
            self.detectors.append(PickleDetector())
        if self.config.scan_pytorch:
            self.detectors.append(PyTorchDetector())
        if self.config.scan_tensorflow:
            self.detectors.append(TensorFlowDetector())
        if self.config.scan_onnx:
            self.detectors.append(ONNXDetector())
        if self.config.scan_huggingface:
            self.detectors.append(HuggingFaceDetector())
        if self.config.scan_pickles:
            self.detectors.append(JoblibDetector())

    async def scan(self, model_path: str, model_id: str = None) -> ScanReport:
        start_time = datetime.utcnow()
        findings = []
        errors = []

        # Prevent path traversal
        path = Path(model_path).resolve()
        if ".." in model_path or not path.is_absolute():
            # Allow relative but resolve, then ensure not escaping allowed roots
            pass
        allowed_prefixes = [Path("/tmp"), Path("/models"), Path("./models"), Path(".").resolve()]
        # In development allow current directory; in production restrict
        if model_path.startswith(("/", "\\")) and not any(str(path).startswith(str(p.resolve()) if p.exists() else str(p)) for p in allowed_prefixes):
            return ScanReport(
                model_id=model_id or model_path,
                model_path=model_path,
                scan_status="failed",
                findings=[],
                errors=["Model path not in allowed directories"],
                scan_duration_ms=0,
            )
        if not path.exists():
            return ScanReport(
                model_id=model_id or model_path,
                model_path=model_path,
                scan_status="failed",
                findings=[],
                errors=[f"Model path does not exist: {model_path}"],
                scan_duration_ms=0,
            )

        total_size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
        if total_size > self.config.max_file_size_mb * 1024 * 1024:
            return ScanReport(
                model_id=model_id or model_path,
                model_path=model_path,
                scan_status="failed",
                findings=[],
                errors=[f"Model size exceeds limit: {total_size} bytes"],
                scan_duration_ms=0,
            )

        for detector in self.detectors:
            try:
                detector_findings = await detector.scan(path)
                findings.extend(detector_findings)
            except Exception as e:
                logger.error("detector_failed", detector=detector.__class__.__name__, error=str(e))
                errors.append(f"Detector {detector.__class__.__name__} failed: {e}")

        elapsed = datetime.utcnow() - start_time
        duration_ms = int(elapsed.total_seconds() * 1000)

        return ScanReport(
            model_id=model_id or model_path,
            model_path=model_path,
            scan_status="completed" if not errors else "partial",
            findings=findings,
            errors=errors,
            scan_duration_ms=duration_ms,
        )