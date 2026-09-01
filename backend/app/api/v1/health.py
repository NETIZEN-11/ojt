from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis
import chromadb
import boto3

from app.api.deps import get_db
from app.core.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "redteam-framework"}


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    checks = {
        "database": False,
        "redis": False,
        "chromadb": False,
        "minio": False,
    }

    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        pass

    try:
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        checks["redis"] = True
    except Exception:
        pass

    try:
        client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
        client.heartbeat()
        checks["chromadb"] = True
    except Exception:
        pass

    try:
        client = boto3.client("s3", endpoint_url=settings.S3_ENDPOINT_URL)
        client.head_bucket(Bucket=settings.S3_BUCKET)
        checks["minio"] = True
    except Exception:
        pass

    all_ready = all(checks.values())
    status_code = 200 if all_ready else 503

    return {"ready": all_ready, "checks": checks}


@router.get("/metrics")
async def metrics():
    from prometheus_client import generate_latest
    from fastapi.responses import Response
    return Response(content=generate_latest(), media_type="text/plain")