import sys
import os
import logging

logging.basicConfig(level=logging.INFO)

# Simulate env vars
os.environ['CELERY_BROKER_URL'] = 'redis://172.26.79.185:6380/0'

try:
    print("Attempting to import backend.generation_tasks...")
    from backend.generation_tasks import generate_batch_task
    print("Import successful!")
except Exception as e:
    print(f"Import failed: {e}")
except KeyboardInterrupt:
    print("Import hung!")
