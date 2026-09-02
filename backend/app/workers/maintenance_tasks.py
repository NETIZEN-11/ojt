import asyncio
from datetime import datetime, timedelta

from celery import shared_task

from app.core.config import get_settings
from app.core.database import get_async_session
from app.core.logging import get_logger
from app.domain.enums import RunStatus
from app.repositories.baselines import AuditLogRepository
from app.repositories.runs import RunRepository

settings = get_settings()
logger = get_logger(__name__)


@shared_task
def cleanup_old_data():
    logger.info("maintenance_cleanup_started")

    async def _run():
        async with get_async_session() as session:
            run_repo = RunRepository(session)
            audit_repo = AuditLogRepository(session)

            cutoff_date = datetime.utcnow() - timedelta(days=settings.TRANSCRIPT_RETENTION_DAYS)
            deleted_runs = await run_repo.delete_old_runs(cutoff_date)
            logger.info("cleaned_old_runs", count=deleted_runs)

            if settings.AUDIT_LOG_RETENTION_DAYS > 0:
                audit_cutoff = datetime.utcnow() - timedelta(days=settings.AUDIT_LOG_RETENTION_DAYS)
                deleted_logs = await audit_repo.delete_old_logs(audit_cutoff)
                logger.info("cleaned_audit_logs", count=deleted_logs)

    asyncio.run(_run())


@shared_task
def check_stuck_runs():
    logger.info("check_stuck_runs_started")

    async def _run():
        async with get_async_session() as session:
            run_repo = RunRepository(session)
            stuck_runs = await run_repo.get_stuck_runs(
                timeout_minutes=settings.CELERY_TASK_TIME_LIMIT // 60
            )
            for run in stuck_runs:
                run.status = RunStatus.FAILED
                run.error_message = "Run timed out / stuck"
                run.completed_at = datetime.utcnow()
                logger.warning("run_marked_failed_stuck", run_id=str(run.id))
            await session.flush()

    asyncio.run(_run())


@shared_task
def health_check_dependencies():
    logger.info("health_check_started")

    async def _run():
        checks = {
            "database": False,
            "redis": False,
            "chromadb": False,
            "minio": False,
        }

        async with get_async_session() as session:
            try:
                await session.execute("SELECT 1")
                checks["database"] = True
            except Exception:
                pass

        import redis

        try:
            r = redis.from_url(settings.REDIS_URL)
            r.ping()
            checks["redis"] = True
        except Exception:
            pass

        import chromadb

        try:
            client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
            client.heartbeat()
            checks["chromadb"] = True
        except Exception:
            pass

        import boto3

        try:
            client = boto3.client("s3", endpoint_url=settings.S3_ENDPOINT_URL)
            client.head_bucket(Bucket=settings.S3_BUCKET)
            checks["minio"] = True
        except Exception:
            pass

        logger.info("health_check_completed", checks=checks)
        return checks

    return asyncio.run(_run())
