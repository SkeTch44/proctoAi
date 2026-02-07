@echo off
set PYTHONPATH=%PYTHONPATH%;%CD%
echo Starting Celery Worker...
celery -A backend.tasks worker --loglevel=info --pool=solo
pause
