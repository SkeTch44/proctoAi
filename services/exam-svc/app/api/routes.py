"""
Exam API routes — /api/v1/exams/*
"""

import json
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_admin, TokenUser
from app.core.database import get_db
from app.models.exam import Exam, ExamSession
from app.schemas import (
    ExamCreate,
    ExamListItem,
    ExamResponse,
    StartExamRequest,
    StartExamResponse,
    SubmitAnswerRequest,
    EndExamResponse,
)

router = APIRouter(prefix="/api/v1/exams", tags=["exams"])


# ------------------------------------------------------------------ #
# GET /  — list all exams
# ------------------------------------------------------------------ #
@router.get("/", response_model=List[ExamListItem])
def list_exams(
    user: TokenUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    exams = db.query(Exam).all()
    return [ExamListItem.model_validate(e) for e in exams]


# ------------------------------------------------------------------ #
# POST /  — create exam (admin/teacher)
# ------------------------------------------------------------------ #
@router.post("/", status_code=status.HTTP_201_CREATED)
def create_exam(
    body: ExamCreate,
    user: TokenUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    exam = Exam(
        title=body.title,
        description=body.description,
        questions=json.dumps(body.questions),
        duration=body.duration,
        created_by=user.user_id,
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return {"exam_id": exam.id, "message": "Exam created successfully"}


# ------------------------------------------------------------------ #
# GET /{exam_id}  — get exam details
# ------------------------------------------------------------------ #
@router.get("/{exam_id}", response_model=ExamResponse)
def get_exam(
    exam_id: int,
    user: TokenUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    questions = json.loads(exam.questions)
    return ExamResponse(
        id=exam.id,
        title=exam.title,
        duration=exam.duration,
        questions=questions,
        totalMarks=len(questions),
        unlocked=True,
    )


# ------------------------------------------------------------------ #
# POST /start  — start an exam session
# ------------------------------------------------------------------ #
@router.post("/start", response_model=StartExamResponse)
def start_exam(
    body: StartExamRequest,
    user: TokenUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    exam = db.query(Exam).filter(Exam.id == body.exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    session = ExamSession(
        exam_id=exam.id,
        user_id=user.user_id,
        status="active",
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    questions = json.loads(exam.questions)
    return StartExamResponse(
        session_id=session.id,
        exam_id=exam.id,
        exam_title=exam.title,
        questions=questions,
        duration=exam.duration,
    )


# ------------------------------------------------------------------ #
# POST /submit-answer  — submit a single answer
# ------------------------------------------------------------------ #
@router.post("/submit-answer")
def submit_answer(
    body: SubmitAnswerRequest,
    user: TokenUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = (
        db.query(ExamSession)
        .filter(ExamSession.id == body.session_id, ExamSession.user_id == user.user_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    answers = json.loads(session.answers or "{}")
    answers[body.question_id] = body.answer
    session.answers = json.dumps(answers)
    db.commit()

    return {"message": "Answer submitted"}


# ------------------------------------------------------------------ #
# POST /end  — end exam session
# ------------------------------------------------------------------ #
@router.post("/end", response_model=EndExamResponse)
def end_exam(
    session_id: int,
    user: TokenUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = (
        db.query(ExamSession)
        .filter(ExamSession.id == session_id, ExamSession.user_id == user.user_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Basic auto-grading: count correct MCQ answers
    exam = db.query(Exam).filter(Exam.id == session.exam_id).first()
    questions = json.loads(exam.questions)
    answers = json.loads(session.answers or "{}")

    correct = 0
    total = len(questions)
    for q in questions:
        q_id = str(q.get("id") or q.get("question_text", ""))
        student_ans = answers.get(q_id)
        correct_ans = (q.get("question_data") or {}).get("correct_answer")
        if student_ans and correct_ans and student_ans.upper() == str(correct_ans).upper():
            correct += 1

    score = round((correct / total * 100) if total > 0 else 0, 2)

    session.score = score
    session.status = "completed"
    session.completed_at = datetime.now(timezone.utc)
    db.commit()

    return EndExamResponse(score=score)
