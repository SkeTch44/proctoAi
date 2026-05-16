"""
Celery application for question-svc background workers.

Start worker:
    celery -A app.workers.celery_app worker --loglevel=info --concurrency=2
"""

from celery import Celery
from app.core.config import get_settings

settings = get_settings()

celery = Celery(
    "question-svc",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=300,  # 5 min soft limit
    task_time_limit=360,       # 6 min hard limit
)
