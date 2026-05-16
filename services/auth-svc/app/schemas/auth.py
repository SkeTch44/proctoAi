"""
Pydantic schemas for auth endpoints.
"""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=150)
    password: str = Field(..., min_length=6, max_length=128)
    email: Optional[str] = None
    role: str = Field(default="student", pattern="^(student|teacher|admin)$")


class LoginRequest(BaseModel):
    identifier: str = Field(..., description="Username or email")
    password: str = Field(..., min_length=1)


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    role: str

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    message: str
    success: bool = True


# Resolve forward reference
TokenResponse.model_rebuild()
