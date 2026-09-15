import time
from functools import wraps

from fastapi import HTTPException, Request, status
from redis import asyncio as aioredis

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


# Redis-based rate limiter for production
class RedisRateLimiter:
    def __init__(self):
        self.redis_client = None
        self._initialized = False
    
    async def _ensure_client(self):
        if not self._initialized:
            try:
                self.redis_client = await aioredis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True
                )
                self._initialized = True
            except Exception as e:
                logger.warning("redis_connection_failed", error=str(e))
                self.redis_client = None
    
    async def check_rate_limit(
        self, key: str, limit: int = None, window: int = None
    ) -> tuple[bool, int, int]:
        limit = limit or settings.RATE_LIMIT_REQUESTS
        window = window or settings.RATE_LIMIT_WINDOW_SECONDS
        
        await self._ensure_client()
        
        if not self.redis_client:
            # Fallback to allowing request if Redis unavailable
            return True, 0, window
        
        try:
            pipe = self.redis_client.pipeline()
            now = time.time()
            key_with_prefix = f"ratelimit:{key}"
            
            # Remove old entries
            pipe.zremrangebyscore(key_with_prefix, 0, now - window)
            # Count current requests
            pipe.zcard(key_with_prefix)
            # Add current request
            pipe.zadd(key_with_prefix, {str(now): now})
            # Set expiration
            pipe.expire(key_with_prefix, window + 1)
            
            results = await pipe.execute()
            current = results[1]
            
            if current >= limit:
                # Get oldest timestamp for retry_after calculation
                oldest = await self.redis_client.zrange(key_with_prefix, 0, 0, withscores=True)
                if oldest:
                    retry_after = int(oldest[0][1] + window - now) + 1
                else:
                    retry_after = window
                return False, current, max(retry_after, 1)
            
            return True, current + 1, window
            
        except Exception as e:
            logger.error("rate_limit_check_failed", error=str(e))
            # Fail open on error to avoid blocking legitimate traffic
            return True, 0, window
    
    async def get_remaining(self, key: str, limit: int = None, window: int = None) -> int:
        limit = limit or settings.RATE_LIMIT_REQUESTS
        window = window or settings.RATE_LIMIT_WINDOW_SECONDS
        
        await self._ensure_client()
        
        if not self.redis_client:
            return limit
        
        try:
            now = time.time()
            key_with_prefix = f"ratelimit:{key}"
            
            # Remove old entries and count
            await self.redis_client.zremrangebyscore(key_with_prefix, 0, now - window)
            current = await self.redis_client.zcard(key_with_prefix)
            
            return max(0, limit - current)
        except Exception:
            return limit


# In-memory fallback for development
class InMemoryRateLimiter:
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

    async def check_rate_limit(
        self, key: str, limit: int = None, window: int = None
    ) -> tuple[bool, int, int]:
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

    async def get_remaining(self, key: str, limit: int = None, window: int = None) -> int:
        limit = limit or settings.RATE_LIMIT_REQUESTS
        window = window or settings.RATE_LIMIT_WINDOW_SECONDS
        self._cleanup()

        now = time.time()
        cutoff = now - window

        if key not in self._windows:
            return limit

        current = len([ts for ts in self._windows[key] if ts > cutoff])
        return max(0, limit - current)


# Use Redis in production, in-memory for development
rate_limiter = RedisRateLimiter() if settings.is_production else InMemoryRateLimiter()


# SECURITY: List of trusted proxy IPs (should be configured via environment)
TRUSTED_PROXY_IPS = {"127.0.0.1", "::1"}  # Add your load balancer IPs here


def _get_client_ip(request: Request) -> str:
    """
    Get client IP with protection against spoofing.
    Only trusts X-Forwarded-For from known proxy IPs.
    """
    client_ip = request.client.host if request.client else "unknown"
    
    # Only trust X-Forwarded-For if request comes from trusted proxy
    if client_ip in TRUSTED_PROXY_IPS:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            # Get the rightmost IP from chain (closest to our proxy)
            # Format: client, proxy1, proxy2, our_proxy
            ips = [ip.strip() for ip in xff.split(",")]
            if ips:
                # Use the leftmost (original client) IP
                return ips[0]
    
    return client_ip


async def rate_limit_dependency(
    request: Request,
    limit: int = None,
    window: int = None,
) -> None:
    client_ip = _get_client_ip(request)
    # Use user ID if authenticated for per-user limiting, else IP + path
    user_key = getattr(request.state, "user_id", None) or client_ip
    key = f"{user_key}:{request.url.path}"
    allowed, current, retry_after = await rate_limiter.check_rate_limit(key, limit, window)

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
            request = kwargs.get("request") or (
                args[0] if args and isinstance(args[0], Request) else None
            )
            if request:
                client_ip = _get_client_ip(request)
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
