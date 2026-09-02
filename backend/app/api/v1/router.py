from fastapi import APIRouter

from app.api.v1 import (
    agents,
    auth,
    baselines,
    health,
    regressions,
    reports,
    results,
    reviews,
    runs,
    settings,
    suites,
    test_cases,
    users,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(suites.router, prefix="/suites", tags=["suites"])
api_router.include_router(test_cases.router, prefix="/test-cases", tags=["test-cases"])
api_router.include_router(runs.router, prefix="/runs", tags=["runs"])
api_router.include_router(results.router, prefix="/results", tags=["results"])
api_router.include_router(regressions.router, prefix="/regressions", tags=["regressions"])
api_router.include_router(baselines.router, prefix="/baselines", tags=["baselines"])
api_router.include_router(reviews.router, prefix="/reviews", tags=["reviews"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(health.router, tags=["health"])
