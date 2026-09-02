import time
from functools import wraps

from fastapi import HTTPException, Request, status

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class RateLimiter:
    def __init__(self):
        self._windows: dict[str, list[float]] = {}
        self._cleanup_interval = 60
        self._last_cleanup = time.time()

    def _cleanup(self):
        now = time.time()
        if now - self._last_cleanup > self._cleanup_interval:
            cutoff = now - settings.RATE_LIMIT_WINDOW_SECONDS
            for key in list(self._windows.keys()):
                self._windows[key] = [ts for ts in self._windows[key] if ts > cutoff]
                if not self._windows[key]:
                    del self._windows[key]
            self._last_cleanup = now

    def check_rate_limit(self, key: str, limit: int = None, window: int = None) -> tuple[bool, int, int]:
        limit = limit or settings.RATE_LIMIT_REQUESTS
        window = window or settings.RATE_LIMIT_WINDOW_SECONDS
        self._cleanup()

        now = time.time()
        cutoff = now - window

        if key not in self._windows:
            self._windows[key] = []

        self._windows[key] = [ts for ts in self._windows[key] if ts > cutoff]
        current = len(self._windows[key])

        if current >= limit:
            retry_after = int(self._windows[key][0] + window - now) + 1
            return False, current, max(retry_after, 1)

        self._windows[key].append(now)
        return True, current + 1, window

    def get_remaining(self, key: str, limit: int = None, window: int = None) -> int:
        limit = limit or settings.RATE_LIMIT_REQUESTS
        window = window or settings.RATE_LIMIT_WINDOW_SECONDS
        self._cleanup()

        now = time.time()
        cutoff = now - window

        if key not in self._windows:
            return limit

        current = len([ts for ts in self._windows[key] if ts > cutoff])
        return max(0, limit - current)


rate_limiter = RateLimiter()


async def rate_limit_dependency(
    request: Request,
    limit: int = None,
    window: int = None,
) -> None:
    client_ip = request.client.host if request.client else "unknown"
    key = f"ratelimit:{client_ip}:{request.url.path}"
    allowed, current, retry_after = rate_limiter.check_rate_limit(key, limit, window)

    remaining = max(0, (limit or settings.RATE_LIMIT_REQUESTS) - current)

    request.state.rate_limit_limit = limit or settings.RATE_LIMIT_REQUESTS
    request.state.rate_limit_remaining = remaining
    request.state.rate_limit_reset = retry_after

    if not allowed:
        logger.warning(
            "rate_limit_exceeded",
            client_ip=client_ip,
            path=request.url.path,
            limit=limit or settings.RATE_LIMIT_REQUESTS,
            window=window or settings.RATE_LIMIT_WINDOW_SECONDS,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={
                "X-RateLimit-Limit": str(limit or settings.RATE_LIMIT_REQUESTS),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(retry_after),
                "Retry-After": str(retry_after),
            },
        )


def rate_limit(limit: int = None, window: int = None):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request") or (args[0] if args and isinstance(args[0], Request) else None)
            if request:
                client_ip = request.client.host if request.client else "unknown"
                key = f"ratelimit:{client_ip}:{request.url.path}"
                allowed, current, retry_after = rate_limiter.check_rate_limit(key, limit, window)
                if not allowed:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Rate limit exceeded",
                        headers={
                            "X-RateLimit-Limit": str(limit or settings.RATE_LIMIT_REQUESTS),
                            "X-RateLimit-Remaining": "0",
                            "X-RateLimit-Reset": str(retry_after),
                            "Retry-After": str(retry_after),
                        },
                    )
            return await func(*args, **kwargs)
        return wrapper
    return decorator
