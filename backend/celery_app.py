import os
from celery import Celery
from backend.utils.logging_config import setup_logging

# Initialize Logging for Worker
setup_logging(name="worker", log_file="worker.log")

def make_celery(app_name=__name__):
    redis_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    return Celery(app_name, broker=redis_url, backend=redis_url, include=['backend.tasks', 'backend.engine.generation_tasks'])

celery = make_celery()
