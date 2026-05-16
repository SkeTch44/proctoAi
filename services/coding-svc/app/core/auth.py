"""Shared JWT auth dependency (same pattern as exam-svc)."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import get_settings

security_scheme = HTTPBearer()


class TokenUser(BaseModel):
    user_id: int
    username: str
    role: str


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> TokenUser:
    settings = get_settings()
    try:
        payload = jwt.decode(
            credentials.credentials, settings.JWT_SECRET_KEY, algorithms=["HS256"]
        )
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    return TokenUser(
        user_id=payload["user_id"],
        username=payload["username"],
        role=payload["role"],
    )
