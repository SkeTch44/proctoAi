"""
Celery tasks for question generation and PDF scanning.

These run in background workers so the API returns immediately.
Progress is reported to Redis so the frontend can poll.
"""

import json
import logging
import os
import sys

# Ensure the monolith backend is importable (reuses existing logic during transition)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import redis
from app.workers.celery_app import celery
from app.core.config import get_settings

logger = logging.getLogger("question-svc.tasks")


def _redis():
    settings = get_settings()
    return redis.from_url(settings.REDIS_URL)


def _update_status(job_id: str, status: str, progress: int = 0, data: dict = None):
    r = _redis()
    payload = {"job_id": job_id, "status": status, "progress": progress}
    if data:
        payload["data"] = data
    r.set(f"job:{job_id}:status", json.dumps(payload), ex=3600)


@celery.task(name="question_svc.generate_questions")
def generate_questions_task(
    job_id: str,
    mode: str,
    topic: str = "",
    count: int = 10,
    difficulty: str = "medium",
    types: list = None,
    file_path: str = None,
):
    """Generate questions (AI or RAG mode)."""
    _update_status(job_id, "processing", 10)

    try:
        from backend.services.question_generation_service import get_question_generation_service
        service = get_question_generation_service()

        if mode == "ai":
            result = service.generate_pure_ai(
                topic=topic,
                count=count,
                difficulty=difficulty,
                question_types=types or ["mcq"],
            )
        elif mode == "rag":
            result = service.generate_rag(
                file_path=file_path,
                topic=topic,
                count=count,
                difficulty=difficulty,
                question_types=types or ["mcq"],
            )
        else:
            result = {"success": False, "message": f"Unknown mode: {mode}"}

        _update_status(job_id, "completed", 100, data=result)

    except Exception as e:
        logger.error(f"Task {job_id} failed: {e}")
        _update_status(job_id, "failed", 0, data={"error": str(e)})
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)


@celery.task(name="question_svc.scan_pdf")
def scan_pdf_task(job_id: str, file_path: str, topic: str = "Extracted Questions"):
    """Scan a PDF and extract existing questions."""
    _update_status(job_id, "processing", 10)

    try:
        from backend.services.question_generation_service import get_question_generation_service
        service = get_question_generation_service()

        result = service.scan_pdf(file_path=file_path, topic=topic)
        _update_status(job_id, "completed", 100, data=result)

    except Exception as e:
        logger.error(f"Scan task {job_id} failed: {e}")
        _update_status(job_id, "failed", 0, data={"error": str(e)})
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
