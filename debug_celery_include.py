import sys
import os
from celery import Celery

# Simulate env vars
os.environ['CELERY_BROKER_URL'] = 'redis://172.26.79.185:6380/0'

try:
    print("Creating Celery app with include=['backend.tasks']...")
    app = Celery('test', include=['backend.tasks'])
    print("App created successfully!")
except Exception as e:
    print(f"Failed: {e}")
except KeyboardInterrupt:
    print("Hung!")
