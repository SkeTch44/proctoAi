"""
Coding Service API — /api/v1/coding/*

Endpoints:
  POST /problems          — Create a coding problem (admin)
  GET  /problems          — List problems
  GET  /problems/{id}     — Get problem details + sample cases
  POST /run               — Run code against sample/custom input (no grading)
  POST /submit            — Submit for full grading
  GET  /submissions/{id}  — Get submission status/result
"""

import json
import logging
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, TokenUser
from app.core.config import get_settings
from app.core.database import get_db
from app.models.problem import Problem, TestCase, Submission
from app.schemas import (
    ProblemCreate,
    ProblemResponse,
    RunRequest,
    RunResponse,
    SubmitRequest,
    SubmitResponse,
    SubmissionStatus,
)

logger = logging.getLogger("coding-svc")
router = APIRouter(prefix="/api/v1/coding", tags=["coding"])


# ------------------------------------------------------------------ #
# POST /problems — create problem (admin/teacher)
# ------------------------------------------------------------------ #
@router.post("/problems", status_code=status.HTTP_201_CREATED)
def create_problem(
    body: ProblemCreate,
    user: TokenUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role not in ("admin", "teacher"):
        raise HTTPException(status_code=403, detail="Only admin/teacher can create problems")

    problem = Problem(
        title=body.title,
        description=body.description,
        difficulty=body.difficulty,
        starter_code=json.dumps(body.starter_code),
        constraints=body.constraints,
        tags=json.dumps(body.tags),
        time_limit_ms=body.time_limit_ms,
        memory_limit_kb=body.memory_limit_kb,
        created_by=user.user_id,
    )
    db.add(problem)
    db.flush()

    # Add test cases
    for i, tc in enumerate(body.test_cases):
        test_case = TestCase(
            problem_id=problem.id,
            input_data=tc.get("input", ""),
            expected_output=tc.get("expected", ""),
            is_sample=tc.get("is_sample", False),
            is_hidden=not tc.get("is_sample", False),
            weight=tc.get("weight", 1.0),
            order_index=i,
        )
        db.add(test_case)

    db.commit()
    return {"problem_id": problem.id, "message": "Problem created"}


# ------------------------------------------------------------------ #
# GET /problems — list problems
# ------------------------------------------------------------------ #
@router.get("/problems", response_model=List[dict])
def list_problems(
    user: TokenUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    problems = db.query(Problem).filter(Problem.is_active == True).all()
    return [
        {
            "id": p.id,
            "title": p.title,
            "difficulty": p.difficulty,
            "tags": json.loads(p.tags or "[]"),
        }
        for p in problems
    ]


# ------------------------------------------------------------------ #
# GET /problems/{id} — get problem + sample cases
# ------------------------------------------------------------------ #
@router.get("/problems/{problem_id}")
def get_problem(
    problem_id: int,
    user: TokenUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    # Only return sample (visible) test cases
    samples = (
        db.query(TestCase)
        .filter(TestCase.problem_id == problem_id, TestCase.is_sample == True)
        .order_by(TestCase.order_index)
        .all()
    )

    return {
        "id": problem.id,
        "title": problem.title,
        "description": problem.description,
        "difficulty": problem.difficulty,
        "starter_code": json.loads(problem.starter_code or "{}"),
        "constraints": problem.constraints,
        "tags": json.loads(problem.tags or "[]"),
        "time_limit_ms": problem.time_limit_ms,
        "memory_limit_kb": problem.memory_limit_kb,
        "sample_cases": [
            {"input": tc.input_data, "expected_output": tc.expected_output}
            for tc in samples
        ],
    }


# ------------------------------------------------------------------ #
# POST /run — run code (no grading, sample/custom input)
# ------------------------------------------------------------------ #
@router.post("/run", response_model=RunResponse)
async def run_code(
    body: RunRequest,
    user: TokenUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.api.judge0 import submit_to_judge0

    settings = get_settings()

    # Determine input
    stdin = body.custom_input or ""
    if not body.custom_input:
        # Use first sample test case
        sample = (
            db.query(TestCase)
            .filter(TestCase.problem_id == body.problem_id, TestCase.is_sample == True)
            .order_by(TestCase.order_index)
            .first()
        )
        if sample:
            stdin = sample.input_data

    result = await submit_to_judge0(
        source_code=body.source_code,
        language=body.language,
        stdin=stdin,
        time_limit=settings.MAX_EXECUTION_TIME_SEC,
        memory_limit=settings.MAX_MEMORY_KB,
    )

    return RunResponse(
        stdout=result.get("stdout", ""),
        stderr=result.get("stderr", "") + (result.get("compile_output") or ""),
        status=result.get("status", "Unknown"),
        execution_time_ms=int(float(result.get("time") or 0) * 1000),
        memory_used_kb=result.get("memory"),
    )


# ------------------------------------------------------------------ #
# POST /submit — submit for full grading
# ------------------------------------------------------------------ #
@router.post("/submit", response_model=SubmitResponse)
async def submit_code(
    body: SubmitRequest,
    user: TokenUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.api.judge0 import submit_to_judge0
    from app.api.ai_scorer import score_submission

    settings = get_settings()

    problem = db.query(Problem).filter(Problem.id == body.problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    # Get ALL test cases (including hidden)
    test_cases = (
        db.query(TestCase)
        .filter(TestCase.problem_id == body.problem_id)
        .order_by(TestCase.order_index)
        .all()
    )

    if not test_cases:
        raise HTTPException(status_code=400, detail="No test cases for this problem")

    # Create submission record
    submission = Submission(
        problem_id=body.problem_id,
        user_id=user.user_id,
        session_id=body.session_id,
        language=body.language,
        source_code=body.source_code,
        status="running",
        tests_total=len(test_cases),
        paste_count=body.paste_count,
        typing_speed_wpm=body.typing_speed_wpm,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    # Run against each test case
    passed = 0
    total_weight = sum(tc.weight for tc in test_cases)
    weighted_score = 0.0
    last_result = {}

    for tc in test_cases:
        result = await submit_to_judge0(
            source_code=body.source_code,
            language=body.language,
            stdin=tc.input_data,
            expected_output=tc.expected_output,
            time_limit=problem.time_limit_ms / 1000.0,
            memory_limit=problem.memory_limit_kb,
        )
        last_result = result

        status_str = result.get("status", "")
        if status_str == "Accepted":
            passed += 1
            weighted_score += tc.weight

        # Store first failure info
        if status_str != "Accepted" and not submission.stderr:
            submission.stderr = result.get("stderr", "")
            submission.compile_output = result.get("compile_output", "")
            submission.stdout = result.get("stdout", "")

    # Update test-based scoring
    test_score = (weighted_score / total_weight * 100) if total_weight > 0 else 0
    final_status = "accepted" if passed == len(test_cases) else "wrong_answer"

    submission.tests_passed = passed
    submission.score = round(test_score, 2)
    submission.status = final_status
    submission.judged_at = datetime.now(timezone.utc)
    submission.execution_time_ms = int(float(last_result.get("time") or 0) * 1000)
    submission.memory_used_kb = last_result.get("memory")

    # AI Code Review — runs async, enriches the submission with rubric
    try:
        ai_result = await score_submission(
            problem_description=problem.description,
            source_code=body.source_code,
            language=body.language,
            tests_passed=passed,
            tests_total=len(test_cases),
            execution_time_ms=submission.execution_time_ms or 0,
            memory_used_kb=submission.memory_used_kb or 0,
        )
        if ai_result:
            import json as _json
            submission.ai_rubric = _json.dumps(ai_result)
            submission.ai_score = float(ai_result.get("total_score", 0))
    except Exception as e:
        logger.warning(f"AI scoring failed for submission {submission.id}: {e}")

    db.commit()

    return SubmitResponse(
        submission_id=submission.id,
        status=final_status,
        message=f"Passed {passed}/{len(test_cases)} test cases (score: {test_score:.1f}%). AI review attached.",
    )


# ------------------------------------------------------------------ #
# GET /submissions/{id} — get submission result
# ------------------------------------------------------------------ #
@router.get("/submissions/{submission_id}", response_model=SubmissionStatus)
def get_submission(
    submission_id: int,
    user: TokenUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Students can only see their own submissions
    if user.role == "student" and sub.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return SubmissionStatus(
        submission_id=sub.id,
        status=sub.status,
        tests_passed=sub.tests_passed,
        tests_total=sub.tests_total,
        score=sub.score,
        stdout=sub.stdout,
        stderr=sub.stderr,
        execution_time_ms=sub.execution_time_ms,
    )


# ================================================================== #
# ADMIN ENDPOINTS — Review & override AI scores
# ================================================================== #

@router.get("/admin/submissions", tags=["admin"])
def list_submissions_for_review(
    user: TokenUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    reviewed: bool = False,
    problem_id: int = None,
):
    """List submissions pending admin review."""
    if user.role not in ("admin", "teacher"):
        raise HTTPException(status_code=403, detail="Admin/teacher access required")

    query = db.query(Submission).filter(Submission.admin_reviewed == reviewed)
    if problem_id:
        query = query.filter(Submission.problem_id == problem_id)

    subs = query.order_by(Submission.submitted_at.desc()).limit(50).all()

    return [
        {
            "id": s.id,
            "problem_id": s.problem_id,
            "user_id": s.user_id,
            "language": s.language,
            "status": s.status,
            "tests_passed": s.tests_passed,
            "tests_total": s.tests_total,
            "score": s.score,
            "ai_score": s.ai_score,
            "ai_rubric": json.loads(s.ai_rubric) if s.ai_rubric else None,
            "paste_count": s.paste_count,
            "typing_speed_wpm": s.typing_speed_wpm,
            "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None,
            "admin_reviewed": s.admin_reviewed,
            "admin_score": s.admin_score,
        }
        for s in subs
    ]


@router.get("/admin/submissions/{submission_id}", tags=["admin"])
def get_submission_detail(
    submission_id: int,
    user: TokenUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get full submission detail including source code and AI rubric."""
    if user.role not in ("admin", "teacher"):
        raise HTTPException(status_code=403, detail="Admin/teacher access required")

    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    problem = db.query(Problem).filter(Problem.id == sub.problem_id).first()

    return {
        "id": sub.id,
        "problem": {
            "id": problem.id if problem else None,
            "title": problem.title if problem else "Unknown",
            "description": problem.description if problem else "",
        },
        "user_id": sub.user_id,
        "language": sub.language,
        "source_code": sub.source_code,
        "status": sub.status,
        "tests_passed": sub.tests_passed,
        "tests_total": sub.tests_total,
        "score": sub.score,
        "ai_score": sub.ai_score,
        "ai_rubric": json.loads(sub.ai_rubric) if sub.ai_rubric else None,
        "stdout": sub.stdout,
        "stderr": sub.stderr,
        "execution_time_ms": sub.execution_time_ms,
        "memory_used_kb": sub.memory_used_kb,
        "paste_count": sub.paste_count,
        "typing_speed_wpm": sub.typing_speed_wpm,
        "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
        "admin_reviewed": sub.admin_reviewed,
        "admin_score": sub.admin_score,
        "admin_feedback": sub.admin_feedback,
    }


from pydantic import BaseModel as _BaseModel


class AdminReviewRequest(_BaseModel):
    score: float = None  # Admin's final score (0-100). If None, accepts AI score.
    feedback: str = ""


@router.post("/admin/submissions/{submission_id}/review", tags=["admin"])
def review_submission(
    submission_id: int,
    body: AdminReviewRequest,
    user: TokenUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Admin reviews and optionally overrides the AI score."""
    if user.role not in ("admin", "teacher"):
        raise HTTPException(status_code=403, detail="Admin/teacher access required")

    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    # If admin provides a score, use it; otherwise accept AI score
    final_score = body.score if body.score is not None else (sub.ai_score or sub.score)

    sub.admin_reviewed = True
    sub.admin_score = final_score
    sub.admin_feedback = body.feedback
    sub.reviewed_by = user.user_id
    sub.reviewed_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "message": "Submission reviewed",
        "submission_id": sub.id,
        "final_score": final_score,
    }
