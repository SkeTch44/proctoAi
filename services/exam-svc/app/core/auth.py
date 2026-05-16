"""
Auth dependency — validates JWT by calling auth-svc's /validate endpoint
or decoding locally (faster, but requires shared secret).

For now we decode locally (shared JWT_SECRET_KEY across services).
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import get_settings

security_scheme = HTTPBearer()

JWT_ALGORITHM = "HS256"


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
            credentials.credentials, settings.JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM]
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    return TokenUser(
        user_id=payload["user_id"],
        username=payload["username"],
        role=payload["role"],
    )


def require_admin(user: TokenUser = Depends(get_current_user)) -> TokenUser:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
