import app.core.sqlite_compat  # noqa: F401 – must be first to patch PG dialect for SQLite
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import close_db, init_db
from app.core.exceptions import RedTeamException, to_http_exception
from app.core.logging import get_logger, setup_logging
from app.core.rate_limit import rate_limit_dependency
from app.core.security import TokenData, require_role
from app.monitoring import security_metrics

settings = get_settings()
logger = get_logger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"
        if settings.is_production:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("application_starting", version=settings.APP_VERSION)

    await init_db()

    yield

    logger.info("application_shutting_down")
    await close_db()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Agent Red-Teaming & Evaluation Framework API",
    lifespan=lifespan,
    # SECURITY: Disable API documentation in production
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
)


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests exceeding size limit to prevent DoS."""

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        max_bytes = 10 * 1024 * 1024  # 10MB
        if content_length:
            try:
                if int(content_length) > max_bytes:
                    return JSONResponse(status_code=413, content={"detail": "Request entity too large"})
            except ValueError:
                pass
        return await call_next(request)


app.add_middleware(RequestSizeLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# Validate CORS origins in production: wildcard not allowed with credentials
cors_origins = settings.cors_origins_list
if settings.is_production and "*" in cors_origins:
    raise RuntimeError("Wildcard CORS origin not allowed in production with credentials")

# In development, allow any localhost port via regex to prevent CORS failures on random Next.js ports (3000-3010)
cors_regex = r"http://localhost:\d+" if settings.is_development else None

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=cors_regex,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX, dependencies=[Depends(rate_limit_dependency)])


@app.get("/api/v1/monitoring/dashboard")
async def monitoring_dashboard(
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "viewer"])),
):
    return security_metrics.get_security_dashboard()


@app.get("/api/v1/monitoring/alerts")
async def monitoring_alerts(
    severity: str | None = None,
    limit: int = 50,
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "viewer"])),
):
    return security_metrics.get_alerts(severity=severity, limit=limit)


def _cors_headers_for_request(request: Request) -> dict[str, str]:
    origin = request.headers.get("origin", "")
    if not origin:
        return {}
    # Allow any localhost port in dev, otherwise check explicit list
    cors_origins = settings.cors_origins_list
    cors_regex = r"http://localhost:\d+" if settings.is_development else None
    allowed = False
    if origin in cors_origins:
        allowed = True
    elif cors_regex:
        import re
        if re.match(cors_regex, origin):
            allowed = True
    if allowed:
        headers: dict[str, str] = {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Vary": "Origin",
        }
        return headers
    return {}


@app.exception_handler(RedTeamException)
async def redteam_exception_handler(request: Request, exc: RedTeamException):
    headers = _cors_headers_for_request(request)
    return JSONResponse(
        status_code=exc.status_code,
        content=to_http_exception(exc).detail,
        headers=headers,
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", error=str(exc), path=request.url.path, exc_info=True)
    headers = _cors_headers_for_request(request)
    return JSONResponse(
        status_code=500,
        content={"code": "INTERNAL_ERROR", "message": "Internal server error"},
        headers=headers,
    )


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "features": {
            "guardrails": "enabled",
            "mcp_proxy": "enabled",
            "code_scanning": "enabled",
            "model_security": "enabled",
            "monitoring": "enabled",
            "red_teaming": "enabled",
            "evaluations": "enabled",
        },
    }