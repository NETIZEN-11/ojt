from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class SeverityLevel(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ScanFinding:
    detector: str
    finding_type: str
    severity: SeverityLevel
    description: str
    file_path: str
    line_number: int = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ScanReport:
    model_id: str
    model_path: str
    scan_status: str
    findings: list[ScanFinding] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    scan_duration_ms: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == SeverityLevel.CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == SeverityLevel.HIGH)

    @property
    def medium_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == SeverityLevel.MEDIUM)

    @property
    def low_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == SeverityLevel.LOW)

    @property
    def info_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == SeverityLevel.INFO)

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "model_path": self.model_path,
            "scan_status": self.scan_status,
            "findings": [
                {
                    "detector": f.detector,
                    "finding_type": f.finding_type,
                    "severity": f.severity.value,
                    "description": f.description,
                    "file_path": f.file_path,
                    "line_number": f.line_number,
                    "metadata": f.metadata,
                    "timestamp": f.timestamp.isoformat(),
                }
                for f in self.findings
            ],
            "errors": self.errors,
            "scan_duration_ms": self.scan_duration_ms,
            "timestamp": self.timestamp.isoformat(),
            "summary": {
                "critical": self.critical_count,
                "high": self.high_count,
                "medium": self.medium_count,
                "low": self.low_count,
                "info": self.info_count,
            },
        }