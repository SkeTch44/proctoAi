from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ExamCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str = ""
    questions: List[Any] = Field(..., min_length=1)
    duration: int = Field(default=3600, gt=0, description="Duration in seconds")
    permissions: Optional[Dict[str, bool]] = None


class ExamListItem(BaseModel):
    id: int
    title: str
    description: str
    duration: int

    class Config:
        from_attributes = True


class ExamResponse(BaseModel):
    id: int
    title: str
    duration: int
    questions: List[Any]
    totalMarks: int
    unlocked: bool = True


class StartExamRequest(BaseModel):
    exam_id: int


class StartExamResponse(BaseModel):
    session_id: int
    exam_id: int
    exam_title: str
    questions: List[Any]
    duration: int


class SubmitAnswerRequest(BaseModel):
    session_id: int
    question_id: str
    answer: str


class EndExamResponse(BaseModel):
    score: float
    message: str = "Exam completed successfully"
