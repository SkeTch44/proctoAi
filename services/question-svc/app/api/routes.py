"""
Question Service API — /api/v1/questions/*

Modes:
  1. POST /generate/ai     — Pure AI generation
  2. POST /generate/rag    — Upload doc → RAG → LLM
  3. POST /scan            — Extract existing questions from PDF
  4. GET  /                — List questions (paginated)
  5. GET  /{id}            — Get single question
"""

import os
import uuid
import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from app.core.config import get_settings

logger = logging.getLogger("question-svc")
router = APIRouter(prefix="/api/v1/questions", tags=["questions"])


# ------------------------------------------------------------------ #
# Schemas
# ------------------------------------------------------------------ #
class AIGenerateRequest(BaseModel):
    topic: str
    count: int = Field(default=10, ge=1, le=50)
    difficulty: str = "medium"
    types: list[str] = ["mcq"]


class GenerateResponse(BaseModel):
    success: bool
    message: str
    count: int = 0
    job_id: Optional[str] = None


# ------------------------------------------------------------------ #
# POST /generate/ai — enqueue pure AI generation
# ------------------------------------------------------------------ #
@router.post("/generate/ai", response_model=GenerateResponse)
def generate_ai(body: AIGenerateRequest):
    """Enqueue AI question generation (async via Celery)."""
    from app.workers.tasks import generate_questions_task

    job_id = f"ai_{uuid.uuid4().hex[:12]}"
    generate_questions_task.delay(
        job_id=job_id,
        mode="ai",
        topic=body.topic,
        count=body.count,
        difficulty=body.difficulty,
        types=body.types,
    )
    return GenerateResponse(
        success=True,
        message="Generation queued",
        job_id=job_id,
    )


# ------------------------------------------------------------------ #
# POST /generate/rag — upload doc + enqueue RAG generation
# ------------------------------------------------------------------ #
@router.post("/generate/rag", response_model=GenerateResponse)
async def generate_rag(
    file: UploadFile = File(...),
    topic: str = Form(default="Document Content"),
    count: int = Form(default=10),
    difficulty: str = Form(default="medium"),
    types: str = Form(default="mcq"),
):
    """Upload a document and generate questions via RAG."""
    settings = get_settings()
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in (".pdf", ".docx", ".doc"):
        raise HTTPException(status_code=400, detail="Only PDF/DOCX allowed")

    save_path = os.path.join(settings.UPLOAD_DIR, f"{uuid.uuid4().hex}{ext}")
    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    from app.workers.tasks import generate_questions_task

    job_id = f"rag_{uuid.uuid4().hex[:12]}"
    generate_questions_task.delay(
        job_id=job_id,
        mode="rag",
        file_path=save_path,
        topic=topic,
        count=count,
        difficulty=difficulty,
        types=types.split(","),
    )
    return GenerateResponse(success=True, message="RAG generation queued", job_id=job_id)


# ------------------------------------------------------------------ #
# POST /scan — extract existing questions from PDF
# ------------------------------------------------------------------ #
@router.post("/scan", response_model=GenerateResponse)
async def scan_pdf(
    file: UploadFile = File(...),
    topic: str = Form(default="Extracted Questions"),
):
    """Scan a question PDF and extract structured questions."""
    settings = get_settings()
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext != ".pdf":
        raise HTTPException(status_code=400, detail="Only PDF allowed for scan")

    save_path = os.path.join(settings.UPLOAD_DIR, f"{uuid.uuid4().hex}.pdf")
    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    from app.workers.tasks import scan_pdf_task

    job_id = f"scan_{uuid.uuid4().hex[:12]}"
    scan_pdf_task.delay(job_id=job_id, file_path=save_path, topic=topic)
    return GenerateResponse(success=True, message="PDF scan queued", job_id=job_id)


# ------------------------------------------------------------------ #
# GET /status/{job_id} — poll job progress
# ------------------------------------------------------------------ #
@router.get("/status/{job_id}")
def get_job_status(job_id: str):
    """Check async job progress."""
    import redis
    settings = get_settings()
    r = redis.from_url(settings.REDIS_URL)
    raw = r.get(f"job:{job_id}:status")
    if not raw:
        return {"job_id": job_id, "status": "unknown"}
    import json
    return json.loads(raw)
