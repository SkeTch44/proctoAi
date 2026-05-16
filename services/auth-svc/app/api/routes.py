"""
Auth API routes — /api/v1/auth/*
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas import (
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.api.deps import get_current_user, require_admin

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# ------------------------------------------------------------------ #
# POST /register
# ------------------------------------------------------------------ #
@router.post(
    "/register",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """Create a new user account."""
    # Check duplicates
    existing = db.query(User).filter(
        or_(User.username == body.username, User.email == body.email)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already exists",
        )

    user = User(
        username=body.username,
        email=body.email,
        password_hash=hash_password(body.password),
        role=body.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return MessageResponse(message=f"User '{user.username}' created (id={user.id})")


# ------------------------------------------------------------------ #
# POST /login
# ------------------------------------------------------------------ #
@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate and return access + refresh tokens."""
    settings = get_settings()

    user = db.query(User).filter(
        or_(User.username == body.identifier, User.email == body.identifier)
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # Account locked?
    if user.locked_until:
        if datetime.now(timezone.utc) < user.locked_until.replace(tzinfo=timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account locked. Try again later.",
            )
        # Lock expired — reset
        user.locked_until = None
        user.login_attempts = 0

    # Verify password
    if not verify_password(body.password, user.password_hash):
        user.login_attempts += 1
        if user.login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
            user.locked_until = datetime.now(timezone.utc) + timedelta(
                minutes=settings.LOCKOUT_MINUTES
            )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # Success — reset attempts, update last_login
    user.login_attempts = 0
    user.locked_until = None
    user.last_login = datetime.now(timezone.utc)
    db.commit()

    # Issue tokens
    token_data = {"user_id": user.id, "username": user.username, "role": user.role}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


# ------------------------------------------------------------------ #
# POST /refresh
# ------------------------------------------------------------------ #
@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    """Exchange a valid refresh token for a new access + refresh pair."""
    payload = decode_token(body.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user_id = payload.get("user_id")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    token_data = {"user_id": user.id, "username": user.username, "role": user.role}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


# ------------------------------------------------------------------ #
# GET /me
# ------------------------------------------------------------------ #
@router.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)):
    """Return the current authenticated user."""
    return UserResponse.model_validate(user)


# ------------------------------------------------------------------ #
# POST /validate (internal — used by other services)
# ------------------------------------------------------------------ #
@router.post("/validate")
def validate_token(
    credentials: dict,
    db: Session = Depends(get_db),
):
    """
    Internal endpoint for other services to validate a token.
    Accepts {"token": "..."} and returns user info or 401.
    """
    token = credentials.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="Token required")

    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    user_id = payload.get("user_id")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return {
        "valid": True,
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
    }
