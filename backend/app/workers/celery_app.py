from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery("redteam_worker")

celery_app.conf.update(
    broker_url=settings.CELERY_BROKER_URL,
    result_backend=settings.CELERY_RESULT_BACKEND,
    task_serializer=settings.CELERY_TASK_SERIALIZER,
    result_serializer=settings.CELERY_RESULT_SERIALIZER,
    accept_content=settings.CELERY_ACCEPT_CONTENT,
    timezone=settings.CELERY_TIMEZONE,
    enable_utc=settings.CELERY_ENABLE_UTC,
    task_track_started=settings.CELERY_TASK_TRACK_STARTED,
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    worker_prefetch_multiplier=settings.CELERY_WORKER_PREFETCH_MULTIPLIER,
    task_routes={
        "app.workers.evaluation_tasks.*": {"queue": "evaluation"},
        "app.workers.redteam_tasks.*": {"queue": "redteam"},
        "app.workers.maintenance_tasks.*": {"queue": "maintenance"},
    },
    task_default_queue="default",
    task_acks_late=True,
    worker_disable_rate_limits=True,
)

celery_app.autodiscover_tasks(["app.workers"])


@celery_app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
