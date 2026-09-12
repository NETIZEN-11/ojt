from fastapi import APIRouter

from app.api.v1 import (
    agents,
    auth,
    baselines,
    datasets,
    health,
    guardrails,
    matrices,
    mcp,
    regressions,
    reports,
    results,
    reviews,
    runs,
    security,
    settings,
    suites,
    test_cases,
    users,
)
from app.api.v1.code_scanning import router as code_scanning_router

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(suites.router, prefix="/suites", tags=["suites"])
api_router.include_router(test_cases.router, prefix="/test-cases", tags=["test-cases"])
api_router.include_router(matrices.router, prefix="/matrices", tags=["matrices"])
api_router.include_router(datasets.router, prefix="/datasets", tags=["datasets"])
api_router.include_router(runs.router, prefix="/runs", tags=["runs"])
api_router.include_router(results.router, prefix="/results", tags=["results"])
api_router.include_router(regressions.router, prefix="/regressions", tags=["regressions"])
api_router.include_router(baselines.router, prefix="/baselines", tags=["baselines"])
api_router.include_router(reviews.router, prefix="/reviews", tags=["reviews"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(guardrails.router, prefix="/guardrails", tags=["guardrails"])
api_router.include_router(mcp.router, prefix="/mcp", tags=["mcp"])
api_router.include_router(code_scanning_router, prefix="/code-scan", tags=["code-scanning"])
api_router.include_router(security.router, prefix="/security", tags=["security"])
api_router.include_router(health.router, tags=["health"])
