from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import close_db, init_db
from app.core.exceptions import RedTeamException, to_http_exception
from app.core.logging import get_logger, setup_logging
from app.core.telemetry import setup_telemetry

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("application_starting", version=settings.APP_VERSION)

    await init_db()

    if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        setup_telemetry(app)

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


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
    }
