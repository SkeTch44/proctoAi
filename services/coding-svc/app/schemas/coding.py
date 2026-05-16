from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ProblemCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str
    difficulty: str = "medium"
    starter_code: Dict[str, str] = {}  # {"python": "def solve():\n    pass"}
    constraints: str = ""
    tags: List[str] = []
    time_limit_ms: int = 2000
    memory_limit_kb: int = 256000
    test_cases: List[Dict[str, Any]] = []  # [{"input": "...", "expected": "...", "is_sample": true}]


class ProblemResponse(BaseModel):
    id: int
    title: str
    description: str
    difficulty: str
    starter_code: Dict[str, str]
    constraints: str
    tags: List[str]
    time_limit_ms: int
    memory_limit_kb: int
    sample_cases: List[Dict[str, str]] = []  # Only visible test cases


class RunRequest(BaseModel):
    """Run code against sample test cases (no grading)."""
    problem_id: int
    language: str
    source_code: str
    custom_input: Optional[str] = None  # If provided, run against this instead of samples


class RunResponse(BaseModel):
    stdout: str = ""
    stderr: str = ""
    status: str = "success"
    execution_time_ms: Optional[int] = None
    memory_used_kb: Optional[int] = None


class SubmitRequest(BaseModel):
    """Submit code for full grading against all test cases."""
    problem_id: int
    language: str
    source_code: str
    session_id: Optional[int] = None
    # Cheat telemetry from frontend
    paste_count: int = 0
    typing_speed_wpm: Optional[float] = None


class SubmitResponse(BaseModel):
    submission_id: int
    status: str = "pending"
    message: str = "Submission queued for judging"


class SubmissionStatus(BaseModel):
    submission_id: int
    status: str
    tests_passed: int = 0
    tests_total: int = 0
    score: float = 0.0
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    execution_time_ms: Optional[int] = None
