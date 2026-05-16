"""
Auth dependency — validates JWT by decoding locally using shared JWT_SECRET_KEY.

Follows the same pattern as exam-svc/app/core/auth.py.
Validates signature, token type ("access"), and expiration on every request.
Returns HTTP 401 with error reason on auth failure.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import ExpiredSignatureError, JWTError, jwt
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
    """Validate JWT and extract user info.

    Verifies:
    - Signature is valid (using JWT_SECRET_KEY)
    - Token type is "access"
    - Token has not expired

    Returns HTTP 401 with specific error reason on failure.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token signature",
        )

    # Validate token type
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type: expected 'access'",
        )

    # Validate required claims
    user_id = payload.get("user_id")
    username = payload.get("username")
    role = payload.get("role")

    if user_id is None or username is None or role is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing required claims",
        )

    return TokenUser(
        user_id=user_id,
        username=username,
        role=role,
    )


def require_role(*allowed_roles: str):
    """Dependency factory that restricts access to specific roles."""

    def _check_role(user: TokenUser = Depends(get_current_user)) -> TokenUser:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {', '.join(allowed_roles)}",
            )
        return user

    return _check_role
