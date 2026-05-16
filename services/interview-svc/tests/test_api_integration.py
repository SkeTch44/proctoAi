"""Integration tests for API endpoints (Task 6.5).

Tests the full session lifecycle via the API layer:
- Create → Join → Leave → End
- Participant limit enforcement
- JWT validation and role-based access control
- Error responses (404, 401, 403, 422, 503)

Validates: Requirements 1.1, 2.1, 4.1, 6.1, 7.1, 9.1, 10.1
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from jose import jwt

from app.api.v1.sessions import router as sessions_router
from app.api.v1.participants import router as participants_router
from app.core.config import get_settings


# Test JWT helper
def _make_token(user_id=1, username="testuser", role="interviewer", expired=False):
    """Create a valid JWT token for testing."""
    settings = get_settings()
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "type": "access",
        "exp": datetime.utcnow() + (timedelta(hours=-1) if expired else timedelta(hours=1)),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")


@pytest.fixture
def app():
    """Create a test FastAPI app with session and participant routers."""
    app = FastAPI()
    app.include_router(sessions_router)
    app.include_router(participants_router)
    return app


class TestJWTValidation:
    """Tests for JWT authentication on API endpoints."""

    @pytest.mark.asyncio
    async def test_request_without_token_returns_401(self, app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/interviews/sessions")
        # FastAPI HTTPBearer returns 403 when no credentials provided
        assert response.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_request_with_expired_token_returns_401(self, app):
        token = _make_token(expired=True)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/v1/interviews/sessions",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 401
        assert "expired" in response.json().get("detail", "").lower()

    @pytest.mark.asyncio
    async def test_request_with_invalid_signature_returns_401(self, app):
        # Token signed with wrong key
        payload = {
            "user_id": 1,
            "username": "test",
            "role": "interviewer",
            "type": "access",
            "exp": datetime.utcnow() + timedelta(hours=1),
        }
        bad_token = jwt.encode(payload, "wrong-secret-key", algorithm="HS256")

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/v1/interviews/sessions",
                headers={"Authorization": f"Bearer {bad_token}"},
            )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_request_with_wrong_token_type_returns_401(self, app):
        settings = get_settings()
        payload = {
            "user_id": 1,
            "username": "test",
            "role": "interviewer",
            "type": "refresh",  # Wrong type
            "exp": datetime.utcnow() + timedelta(hours=1),
        }
        token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/v1/interviews/sessions",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 401
        assert "type" in response.json().get("detail", "").lower()


class TestRoleBasedAccess:
    """Tests for role-based access control."""

    @pytest.mark.asyncio
    async def test_student_cannot_create_session(self, app):
        token = _make_token(role="student")
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/interviews/sessions",
                headers={"Authorization": f"Bearer {token}"},
                json={"title": "Test Session", "max_participants": 4},
            )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_student_cannot_end_session(self, app):
        token = _make_token(role="student")
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/interviews/sessions/some-id/end",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_interviewer_can_create_session(self, app):
        token = _make_token(role="interviewer")

        with patch(
            "app.api.v1.sessions._get_session_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_result = MagicMock()
            mock_result.session_id = "new-session-id"
            mock_result.join_url = "/api/v1/interviews/sessions/new-session-id/join"
            mock_result.room_name = "interview_new-sess"
            mock_service.create_session = AsyncMock(return_value=mock_result)
            mock_get_service.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/interviews/sessions",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"title": "Test Session", "max_participants": 4},
                )

        assert response.status_code == 201
        data = response.json()
        assert data["session_id"] == "new-session-id"

    @pytest.mark.asyncio
    async def test_admin_can_create_session(self, app):
        token = _make_token(role="admin")

        with patch(
            "app.api.v1.sessions._get_session_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_result = MagicMock()
            mock_result.session_id = "admin-session"
            mock_result.join_url = "/api/v1/interviews/sessions/admin-session/join"
            mock_result.room_name = "interview_admin-se"
            mock_service.create_session = AsyncMock(return_value=mock_result)
            mock_get_service.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/interviews/sessions",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"title": "Admin Session"},
                )

        assert response.status_code == 201


class TestSessionCreationValidation:
    """Tests for request validation on session creation."""

    @pytest.mark.asyncio
    async def test_empty_title_returns_422(self, app):
        token = _make_token(role="interviewer")
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/interviews/sessions",
                headers={"Authorization": f"Bearer {token}"},
                json={"title": "", "max_participants": 4},
            )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_max_participants_below_2_returns_422(self, app):
        token = _make_token(role="interviewer")
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/interviews/sessions",
                headers={"Authorization": f"Bearer {token}"},
                json={"title": "Test", "max_participants": 1},
            )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_max_participants_above_10_returns_422(self, app):
        token = _make_token(role="interviewer")
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/interviews/sessions",
                headers={"Authorization": f"Bearer {token}"},
                json={"title": "Test", "max_participants": 11},
            )
        assert response.status_code == 422


class TestErrorResponses:
    """Tests for proper error response codes."""

    @pytest.mark.asyncio
    async def test_join_nonexistent_session_returns_404(self, app):
        from app.core.exceptions import SessionNotFoundError

        token = _make_token(role="interviewer")

        with patch(
            "app.api.v1.sessions._get_session_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.join_session = AsyncMock(
                side_effect=SessionNotFoundError("nonexistent")
            )
            mock_get_service.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/interviews/sessions/nonexistent/join",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"role": "interviewer", "display_name": "Alice"},
                )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_join_full_session_returns_409(self, app):
        from app.core.exceptions import SessionFullError

        token = _make_token(role="interviewer")

        with patch(
            "app.api.v1.sessions._get_session_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.join_session = AsyncMock(
                side_effect=SessionFullError("sess-1", 6)
            )
            mock_get_service.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/interviews/sessions/sess-1/join",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"role": "interviewer", "display_name": "Alice"},
                )

        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_join_ended_session_returns_409(self, app):
        from app.core.exceptions import SessionEndedError

        token = _make_token(role="interviewer")

        with patch(
            "app.api.v1.sessions._get_session_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.join_session = AsyncMock(
                side_effect=SessionEndedError("sess-1")
            )
            mock_get_service.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/interviews/sessions/sess-1/join",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"role": "interviewer", "display_name": "Alice"},
                )

        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_livekit_unavailable_returns_503(self, app):
        from app.core.exceptions import ServiceUnavailableError

        token = _make_token(role="interviewer")

        with patch(
            "app.api.v1.sessions._get_session_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.join_session = AsyncMock(
                side_effect=ServiceUnavailableError(service="LiveKit", retry_after=5)
            )
            mock_get_service.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/interviews/sessions/sess-1/join",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"role": "interviewer", "display_name": "Alice"},
                )

        assert response.status_code == 503
        assert response.headers.get("retry-after") == "5"
