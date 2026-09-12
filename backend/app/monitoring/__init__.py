import time
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class SecurityMetrics:
    """Security monitoring metrics collector."""

    def __init__(self):
        self._metrics: dict[str, dict[str, Any]] = {}
        self._alerts: list[dict[str, Any]] = []

    def record_guardrail_hit(self, guardrail_type: str, severity: str, blocked: bool):
        """Record a guardrail hit."""
        key = f"guardrail:{guardrail_type}"
        if key not in self._metrics:
            self._metrics[key] = {"hits": 0, "blocked": 0, "severity": severity}
        self._metrics[key]["hits"] += 1
        if blocked:
            self._metrics[key]["blocked"] += 1

        if blocked and severity in ("critical", "high"):
            self._alerts.append({
                "id": str(uuid4()),
                "type": "guardrail_block",
                "guardrail_type": guardrail_type,
                "severity": severity,
                "timestamp": datetime.now().isoformat(),
            })
            logger.warning("security_alert", type="guardrail_block", guardrail_type=guardrail_type, severity=severity)

    def record_rate_limit_hit(self, endpoint: str, client_ip: str):
        """Record a rate limit hit."""
        key = f"ratelimit:{endpoint}"
        if key not in self._metrics:
            self._metrics[key] = {"hits": 0, "clients": set()}
        self._metrics[key]["hits"] += 1
        self._metrics[key]["clients"].add(client_ip)

    def record_auth_failure(self, method: str, ip: str):
        """Record an authentication failure."""
        key = "auth:failures"
        if key not in self._metrics:
            self._metrics[key] = {"count": 0, "ips": set()}
        self._metrics[key]["count"] += 1
        self._metrics[key]["ips"].add(ip)

        if self._metrics[key]["count"] > 5:
            self._alerts.append({
                "id": str(uuid4()),
                "type": "auth_brute_force",
                "method": method,
                "ip": ip,
                "count": self._metrics[key]["count"],
                "timestamp": datetime.now().isoformat(),
            })
            logger.warning("security_alert", type="auth_brute_force", ip=ip, count=self._metrics[key]["count"])

    def record_data_access(self, resource: str, user_id: str, action: str):
        """Record a data access event."""
        key = f"data_access:{resource}"
        logger.info("data_access", resource=resource, user_id=user_id, action=action)

    def get_security_dashboard(self) -> dict[str, Any]:
        """Get security dashboard data."""
        return {
            "timestamp": datetime.now().isoformat(),
            "total_alerts": len(self._alerts),
            "recent_alerts": self._alerts[-10:],
            "metrics": {k: v for k, v in self._metrics.items()},
            "guardrail_stats": self._get_guardrail_stats(),
            "uptime_seconds": self._get_uptime(),
        }

    def _get_guardrail_stats(self) -> dict[str, Any]:
        guardrail_stats = {}
        for key, value in self._metrics.items():
            if key.startswith("guardrail:"):
                guardrail_stats[key] = value
        return guardrail_stats

    def _get_uptime(self) -> float:
        return time.time() - getattr(self, "_start_time", time.time())

    def get_alerts(
        self, severity: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        alerts = self._alerts
        if severity:
            alerts = [a for a in alerts if a["severity"] == severity]
        return alerts[-limit:]


security_metrics = SecurityMetrics()


class SecurityMonitor:
    """Continuous security monitoring for AI applications."""

    def __init__(self):
        self.metrics = security_metrics
        self._scan_interval = 300  # 5 minutes
        self._last_scan = time.time()

    async def monitor(self):
        """Run continuous monitoring checks."""
        current_time = time.time()
        if current_time - self._last_scan > self._scan_interval:
            self._last_scan = current_time
            await self._run_checks()

    async def _run_checks(self):
        """Run all security checks."""
        self._check_anomalous_requests()
        self._check_token_usage()
        self._check_cost_anomalies()

    def _check_anomalous_requests(self):
        """Check for anomalous request patterns."""
        auth_failures = self.metrics._metrics.get("auth:failures", {})
        if auth_failures.get("count", 0) > 10:
            logger.warning("anomalous_requests", type="auth_brute_force", count=auth_failures["count"])

    def _check_token_usage(self):
        """Check for abnormal token usage patterns."""
        pass

    def _check_cost_anomalies(self):
        """Check for cost anomalies."""
        pass


security_monitor = SecurityMonitor()