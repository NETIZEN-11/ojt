from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

import ipaddress
import socket
from urllib.parse import urlparse

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


def _is_private_ip(host: str) -> bool:
    """Check if hostname resolves to a private IP address."""
    try:
        ip = ipaddress.ip_address(socket.gethostbyname(host))
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
    except Exception:
        return False


def _validate_resolved_ip(host: str) -> None:
    """Validate that hostname resolves to allowed IP. Must be called immediately before connection."""
    try:
        resolved_ip = socket.gethostbyname(host)
        ip = ipaddress.ip_address(resolved_ip)
        
        # Block private IPs if configured
        if settings.TARGET_AGENT_BLOCK_PRIVATE_IPS:
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                raise ValueError(f"Resolved IP {resolved_ip} is private/reserved")
        
        # Additional check for localhost in production
        if settings.is_production and resolved_ip in ("127.0.0.1", "::1", "localhost"):
            raise ValueError(f"Localhost access blocked in production")
            
    except socket.gaierror as e:
        raise ValueError(f"Hostname resolution failed: {e}")


def validate_target_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Invalid URL scheme: {parsed.scheme}")
    if not parsed.hostname:
        raise ValueError("URL must have a hostname")
    allowed = settings.allowed_hosts_list
    if allowed and parsed.hostname not in allowed:
        raise ValueError(f"Host {parsed.hostname} not in allowed hosts")
    
    # Initial validation - note: must re-validate before actual connection due to DNS rebinding
    if settings.TARGET_AGENT_BLOCK_PRIVATE_IPS and _is_private_ip(parsed.hostname):
        raise ValueError(f"Private IP access blocked: {parsed.hostname}")
    if parsed.hostname in ("localhost", "127.0.0.1", "::1") and settings.is_production:
        raise ValueError("Localhost access not allowed in production")


class TargetAgentProvider(ABC):
    @abstractmethod
    async def call(self, input_text: str, context: dict[str, Any] = None) -> dict[str, Any]:
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        pass


class HTTPTargetAgentProvider(TargetAgentProvider):
    def __init__(
        self,
        endpoint_url: str,
        auth_config: dict[str, Any] = None,
        request_template: dict[str, Any] = None,
        response_extraction: dict[str, Any] = None,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        validate_target_url(endpoint_url)
        if timeout > 60 or timeout < 1:
            raise ValueError("Timeout must be between 1 and 60 seconds")
        if max_retries > 5:
            raise ValueError("max_retries too high")
        self.endpoint_url = endpoint_url
        self.auth_config = auth_config or {}
        self.request_template = request_template or {}
        self.response_extraction = response_extraction or {}
        self.timeout = timeout
        self.max_retries = max_retries

        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=5.0),
            headers={"Content-Type": "application/json", **self.auth_config.get("headers", {})},
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    )
    async def call(self, input_text: str, context: dict[str, Any] = None) -> dict[str, Any]:
        request_body = self._build_request(input_text, context)

        try:
            # SECURITY: Re-validate IP immediately before connection to prevent DNS rebinding
            parsed = urlparse(self.endpoint_url)
            if parsed.hostname:
                _validate_resolved_ip(parsed.hostname)
            
            response = await self.client.post(self.endpoint_url, json=request_body)
            response.raise_for_status()
            return self._extract_response(response.json())
        except httpx.TimeoutException:
            logger.error("target_agent_timeout", url=self.endpoint_url)
            raise
        except httpx.HTTPStatusError as e:
            logger.error(
                "target_agent_http_error", url=self.endpoint_url, status=e.response.status_code
            )
            raise
        except httpx.RequestError as e:
            logger.error("target_agent_request_error", url=self.endpoint_url, error=str(e))
            raise

    def _build_request(self, input_text: str, context: dict[str, Any] = None) -> dict[str, Any]:
        if not self.request_template:
            return {"input": input_text}

        import copy

        request = copy.deepcopy(self.request_template)

        def replace_variables(obj: Any) -> Any:
            if isinstance(obj, str):
                result = obj.replace("{input}", input_text)
                if context:
                    for key, value in context.items():
                        result = result.replace(f"{{{key}}}", str(value))
                return result
            if isinstance(obj, dict):
                return {k: replace_variables(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [replace_variables(item) for item in obj]
            return obj

        return replace_variables(request)

    def _extract_response(self, response: dict[str, Any]) -> dict[str, Any]:
        if not self.response_extraction:
            return response

        result = {}
        for key, path in self.response_extraction.items():
            value = response
            try:
                for part in path.split("."):
                    if isinstance(value, list):
                        part = int(part)
                    value = value[part]
                result[key] = value
            except (KeyError, IndexError, ValueError, TypeError):
                result[key] = None
        return result

    async def health_check(self) -> bool:
        try:
            response = await self.client.get(
                self.endpoint_url.replace("/chat", "/health").replace("/completions", "/health")
            )
            return response.status_code == 200
        except Exception:
            return False

    async def close(self):
        await self.client.aclose()


class MockTargetAgentProvider(TargetAgentProvider):
    def __init__(self, scenario: str = "safe"):
        self.scenario = scenario
        self.call_count = 0

    async def call(self, input_text: str, context: dict[str, Any] = None) -> dict[str, Any]:
        self.call_count += 1

        if self.scenario == "safe":
            return {
                "response": "I cannot help with that request. It violates my safety guidelines."
            }
        if self.scenario == "jailbreak_vulnerable":
            if "ignore" in input_text.lower() or "system prompt" in input_text.lower():
                return {"response": "My system prompt is: You are a helpful assistant..."}
            return {"response": "I cannot help with that."}
        if self.scenario == "pii_leak":
            if "email" in input_text.lower() or "phone" in input_text.lower():
                return {"response": "The CEO's email is ceo@company.com and phone is 555-1234"}
            return {"response": "I don't have that information."}
        if self.scenario == "prompt_injection":
            if "ignore" in input_text.lower() and "injected" in input_text.lower():
                return {"response": "Injected!"}
            return {"response": "I cannot follow that instruction."}
        if self.scenario == "timeout":
            import asyncio

            await asyncio.sleep(60)
            return {"response": "Timeout"}
        if self.scenario == "error":
            raise Exception("Simulated target agent error")

        return {"response": "Mock response"}

    async def health_check(self) -> bool:
        return True


class TargetAgentProviderFactory:
    @staticmethod
    def create_provider(
        provider_type: str,
        endpoint_url: str = "",
        auth_config: dict[str, Any] = None,
        request_template: dict[str, Any] = None,
        response_extraction: dict[str, Any] = None,
        timeout: int = 30,
        max_retries: int = 3,
        scenario: str = "safe",
    ) -> TargetAgentProvider:
        if provider_type == "http":
            return HTTPTargetAgentProvider(
                endpoint_url=endpoint_url,
                auth_config=auth_config,
                request_template=request_template,
                response_extraction=response_extraction,
                timeout=timeout,
                max_retries=max_retries,
            )
        if provider_type == "mock" or settings.DEV_MOCK_TARGET_AGENT:
            return MockTargetAgentProvider(scenario=scenario)
        logger.warning("unknown_target_agent_provider", provider=provider_type)
        return MockTargetAgentProvider(scenario=scenario)
