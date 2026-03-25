@echo off
set PYTHONPATH=%PYTHONPATH%;%CD%
echo Starting Celery Worker...
celery -A backend.celery_app worker --loglevel=info --pool=solo --concurrency=1
pause
