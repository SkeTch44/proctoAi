import os
from celery import Celery

def make_celery(app_name=__name__):
    redis_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    return Celery(app_name, broker=redis_url, backend=redis_url)

celery = make_celery()
