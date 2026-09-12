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
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX, dependencies=[Depends(rate_limit_dependency)])


@app.get("/api/v1/monitoring/dashboard")
async def monitoring_dashboard():
    return security_metrics.get_security_dashboard()


@app.get("/api/v1/monitoring/alerts")
async def monitoring_alerts(severity: str | None = None, limit: int = 50):
    return security_metrics.get_alerts(severity=severity, limit=limit)


@app.exception_handler(RedTeamException)
async def redteam_exception_handler(request: Request, exc: RedTeamException):
    return JSONResponse(
        status_code=exc.status_code,
        content=to_http_exception(exc).detail,
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", error=str(exc), path=request.url.path, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"code": "INTERNAL_ERROR", "message": "Internal server error"},
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