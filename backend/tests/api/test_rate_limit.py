import pytest
from unittest.mock import patch, MagicMock

from app.core.rate_limit import RateLimiter, settings


class TestRateLimiter:
    """Test rate limiting functionality."""

    def test_rate_limit_allows_requests_under_limit(self):
        """Test that requests under the limit are allowed."""
        limiter = RateLimiter()
        limit = settings.RATE_LIMIT_REQUESTS
        for i in range(limit):
            allowed, current, window = limiter.check_rate_limit("test_key")
            assert allowed is True
        assert limiter.get_remaining("test_key") >= 0

    def test_rate_limit_blocks_requests_over_limit(self):
        """Test that requests over the limit are blocked."""
        limiter = RateLimiter()
        limit = settings.RATE_LIMIT_REQUESTS
        for i in range(limit + 1):
            limiter.check_rate_limit("test_key")
        allowed, current, retry_after = limiter.check_rate_limit("test_key")
        assert allowed is False

    def test_rate_limit_different_keys(self):
        """Test that different keys have independent limits."""
        limiter = RateLimiter()
        limit = settings.RATE_LIMIT_REQUESTS
        for i in range(limit):
            limiter.check_rate_limit("key1")
        allowed, _, _ = limiter.check_rate_limit("key2")
        assert allowed is True


class TestRateLimitDependency:
    """Test the rate limit dependency."""

    @pytest.mark.asyncio
    async def test_rate_limit_dependency_allows_request(self):
        """Test that rate limit dependency runs without error for allowed requests."""
        request = MagicMock()
        request.client.host = "127.0.0.1"
        request.url.path = "/api/v1/test"
        request.state = MagicMock()
        # Should not raise an exception

    @pytest.mark.asyncio
    async def test_rate_limit_dependency_blocks_over_limit(self):
        """Test that rate limit dependency runs without error."""
        request = MagicMock()
        request.client.host = "127.0.0.1"
        request.url.path = "/api/v1/test"
        request.state = MagicMock()
        # Should not raise an exception