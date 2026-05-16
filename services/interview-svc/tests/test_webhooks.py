"""Unit tests for LiveKit webhook handler."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.api.v1.webhooks import router


@pytest.fixture
def app():
    """Create a FastAPI app with the webhooks router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def mock_webhook_event():
    """Create a mock WebhookEvent with participant_disconnected data."""
    event = MagicMock()
    event.event = "participant_disconnected"
    event.room = MagicMock()
    event.room.name = "interview_abc12345"
    event.participant = MagicMock()
    event.participant.identity = "42"
    event.participant.name = "Alice"
    return event


@pytest.fixture
def mock_room_finished_event():
    """Create a mock WebhookEvent with room_finished data."""
    event = MagicMock()
    event.event = "room_finished"
    event.room = MagicMock()
    event.room.name = "interview_abc12345"
    event.participant = None
    return event


@pytest.fixture
def mock_session():
    """Create a mock InterviewSession."""
    session = MagicMock()
    session.id = "abc12345-full-uuid"
    session.room_name = "interview_abc12345"
    session.status = "active"
    session.ended_at = None
    return session


@pytest.fixture
def mock_participant():
    """Create a mock SessionParticipant."""
    participant = MagicMock()
    participant.user_id = 42
    participant.role = "interviewer"
    participant.status = "connected"
    participant.left_at = None
    return participant


class TestWebhookSignatureValidation:
    """Tests for webhook signature validation."""

    @pytest.mark.asyncio
    async def test_rejects_request_without_authorization_header(self, app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/interviews/webhooks/livekit",
                content='{"event": "test"}',
            )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_rejects_request_with_invalid_signature(self, app):
        with patch(
            "app.api.v1.webhooks._get_webhook_receiver"
        ) as mock_get_receiver:
            receiver = MagicMock()
            receiver.receive.side_effect = Exception("Invalid token")
            mock_get_receiver.return_value = receiver

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/interviews/webhooks/livekit",
                    content='{"event": "test"}',
                    headers={"Authorization": "invalid-token"},
                )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_accepts_request_with_valid_signature(self, app, mock_webhook_event):
        with patch(
            "app.api.v1.webhooks._get_webhook_receiver"
        ) as mock_get_receiver, patch(
            "app.api.v1.webhooks._handle_participant_disconnected",
            new_callable=AsyncMock,
        ):
            receiver = MagicMock()
            receiver.receive.return_value = mock_webhook_event
            mock_get_receiver.return_value = receiver

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/interviews/webhooks/livekit",
                    content='{"event": "participant_disconnected"}',
                    headers={"Authorization": "valid-token"},
                )
        assert response.status_code == 200


class TestParticipantDisconnected:
    """Tests for participant_disconnected event handling."""

    @pytest.mark.asyncio
    async def test_updates_participant_status_to_disconnected(
        self, app, mock_webhook_event, mock_session, mock_participant
    ):
        mock_db = AsyncMock()

        # First query: find session by room_name
        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = mock_session

        # Second query: find participant by user_id and session_id
        participant_result = MagicMock()
        participant_result.scalar_one_or_none.return_value = mock_participant

        # Third query: count remaining interviewers
        count_result = MagicMock()
        count_result.scalar.return_value = 0

        mock_db.execute = AsyncMock(
            side_effect=[session_result, participant_result, count_result]
        )
        mock_db.commit = AsyncMock()

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.api.v1.webhooks._get_webhook_receiver"
        ) as mock_get_receiver, patch(
            "app.api.v1.webhooks.get_async_session_factory",
            return_value=mock_session_factory,
        ), patch(
            "app.api.v1.webhooks.get_timeout_manager"
        ) as mock_get_tm:
            receiver = MagicMock()
            receiver.receive.return_value = mock_webhook_event
            mock_get_receiver.return_value = receiver

            mock_tm = AsyncMock()
            mock_get_tm.return_value = mock_tm

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/interviews/webhooks/livekit",
                    content='{"event": "participant_disconnected"}',
                    headers={"Authorization": "valid-token"},
                )

        assert response.status_code == 200
        assert mock_participant.status == "disconnected"
        assert mock_participant.left_at is not None
        # Last interviewer left, so timeout should be started
        mock_tm.start_timeout.assert_called_once_with(mock_session.id)

    @pytest.mark.asyncio
    async def test_does_not_start_timeout_if_interviewers_remain(
        self, app, mock_webhook_event, mock_session, mock_participant
    ):
        mock_db = AsyncMock()

        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = mock_session

        participant_result = MagicMock()
        participant_result.scalar_one_or_none.return_value = mock_participant

        # 1 interviewer still connected
        count_result = MagicMock()
        count_result.scalar.return_value = 1

        mock_db.execute = AsyncMock(
            side_effect=[session_result, participant_result, count_result]
        )
        mock_db.commit = AsyncMock()

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.api.v1.webhooks._get_webhook_receiver"
        ) as mock_get_receiver, patch(
            "app.api.v1.webhooks.get_async_session_factory",
            return_value=mock_session_factory,
        ), patch(
            "app.api.v1.webhooks.get_timeout_manager"
        ) as mock_get_tm:
            receiver = MagicMock()
            receiver.receive.return_value = mock_webhook_event
            mock_get_receiver.return_value = receiver

            mock_tm = AsyncMock()
            mock_get_tm.return_value = mock_tm

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/interviews/webhooks/livekit",
                    content='{"event": "participant_disconnected"}',
                    headers={"Authorization": "valid-token"},
                )

        assert response.status_code == 200
        mock_tm.start_timeout.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_non_interviewer_disconnect_timeout_check(
        self, app, mock_webhook_event, mock_session, mock_participant
    ):
        # Participant is an interviewee, not an interviewer
        mock_participant.role = "interviewee"

        mock_db = AsyncMock()

        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = mock_session

        participant_result = MagicMock()
        participant_result.scalar_one_or_none.return_value = mock_participant

        mock_db.execute = AsyncMock(
            side_effect=[session_result, participant_result]
        )
        mock_db.commit = AsyncMock()

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.api.v1.webhooks._get_webhook_receiver"
        ) as mock_get_receiver, patch(
            "app.api.v1.webhooks.get_async_session_factory",
            return_value=mock_session_factory,
        ), patch(
            "app.api.v1.webhooks.get_timeout_manager"
        ) as mock_get_tm:
            receiver = MagicMock()
            receiver.receive.return_value = mock_webhook_event
            mock_get_receiver.return_value = receiver

            mock_tm = AsyncMock()
            mock_get_tm.return_value = mock_tm

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/interviews/webhooks/livekit",
                    content='{"event": "participant_disconnected"}',
                    headers={"Authorization": "valid-token"},
                )

        assert response.status_code == 200
        assert mock_participant.status == "disconnected"
        # No timeout check for non-interviewers
        mock_tm.start_timeout.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_already_disconnected_participant(
        self, app, mock_webhook_event, mock_session, mock_participant
    ):
        mock_participant.status = "disconnected"

        mock_db = AsyncMock()

        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = mock_session

        participant_result = MagicMock()
        participant_result.scalar_one_or_none.return_value = mock_participant

        mock_db.execute = AsyncMock(
            side_effect=[session_result, participant_result]
        )
        mock_db.commit = AsyncMock()

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.api.v1.webhooks._get_webhook_receiver"
        ) as mock_get_receiver, patch(
            "app.api.v1.webhooks.get_async_session_factory",
            return_value=mock_session_factory,
        ):
            receiver = MagicMock()
            receiver.receive.return_value = mock_webhook_event
            mock_get_receiver.return_value = receiver

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/interviews/webhooks/livekit",
                    content='{"event": "participant_disconnected"}',
                    headers={"Authorization": "valid-token"},
                )

        assert response.status_code == 200
        # commit should not be called since participant was already disconnected
        mock_db.commit.assert_not_called()


class TestRoomFinished:
    """Tests for room_finished event handling."""

    @pytest.mark.asyncio
    async def test_ends_active_session_on_room_finished(
        self, app, mock_room_finished_event, mock_session
    ):
        mock_db = AsyncMock()

        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = mock_session

        # Connected participants query
        participants_scalars = MagicMock()
        participants_scalars.all.return_value = []
        participants_result = MagicMock()
        participants_result.scalars.return_value = participants_scalars

        mock_db.execute = AsyncMock(
            side_effect=[session_result, participants_result]
        )
        mock_db.commit = AsyncMock()

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.api.v1.webhooks._get_webhook_receiver"
        ) as mock_get_receiver, patch(
            "app.api.v1.webhooks.get_async_session_factory",
            return_value=mock_session_factory,
        ), patch(
            "app.api.v1.webhooks.get_timeout_manager"
        ) as mock_get_tm:
            receiver = MagicMock()
            receiver.receive.return_value = mock_room_finished_event
            mock_get_receiver.return_value = receiver

            mock_tm = AsyncMock()
            mock_get_tm.return_value = mock_tm

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/interviews/webhooks/livekit",
                    content='{"event": "room_finished"}',
                    headers={"Authorization": "valid-token"},
                )

        assert response.status_code == 200
        assert mock_session.status == "ended"
        assert mock_session.ended_at is not None
        mock_tm.cancel_timeout.assert_called_once_with(mock_session.id)

    @pytest.mark.asyncio
    async def test_skips_already_ended_session(
        self, app, mock_room_finished_event, mock_session
    ):
        mock_session.status = "ended"

        mock_db = AsyncMock()

        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = mock_session

        mock_db.execute = AsyncMock(side_effect=[session_result])
        mock_db.commit = AsyncMock()

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.api.v1.webhooks._get_webhook_receiver"
        ) as mock_get_receiver, patch(
            "app.api.v1.webhooks.get_async_session_factory",
            return_value=mock_session_factory,
        ):
            receiver = MagicMock()
            receiver.receive.return_value = mock_room_finished_event
            mock_get_receiver.return_value = receiver

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/interviews/webhooks/livekit",
                    content='{"event": "room_finished"}',
                    headers={"Authorization": "valid-token"},
                )

        assert response.status_code == 200
        # Should not commit since session was already ended
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_disconnects_remaining_participants_on_room_finished(
        self, app, mock_room_finished_event, mock_session
    ):
        mock_p1 = MagicMock()
        mock_p1.status = "connected"
        mock_p1.left_at = None
        mock_p2 = MagicMock()
        mock_p2.status = "connected"
        mock_p2.left_at = None

        mock_db = AsyncMock()

        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = mock_session

        participants_scalars = MagicMock()
        participants_scalars.all.return_value = [mock_p1, mock_p2]
        participants_result = MagicMock()
        participants_result.scalars.return_value = participants_scalars

        mock_db.execute = AsyncMock(
            side_effect=[session_result, participants_result]
        )
        mock_db.commit = AsyncMock()

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.api.v1.webhooks._get_webhook_receiver"
        ) as mock_get_receiver, patch(
            "app.api.v1.webhooks.get_async_session_factory",
            return_value=mock_session_factory,
        ), patch(
            "app.api.v1.webhooks.get_timeout_manager"
        ) as mock_get_tm:
            receiver = MagicMock()
            receiver.receive.return_value = mock_room_finished_event
            mock_get_receiver.return_value = receiver

            mock_tm = AsyncMock()
            mock_get_tm.return_value = mock_tm

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/interviews/webhooks/livekit",
                    content='{"event": "room_finished"}',
                    headers={"Authorization": "valid-token"},
                )

        assert response.status_code == 200
        assert mock_p1.status == "disconnected"
        assert mock_p1.left_at is not None
        assert mock_p2.status == "disconnected"
        assert mock_p2.left_at is not None


class TestUnhandledEvents:
    """Tests for unhandled event types."""

    @pytest.mark.asyncio
    async def test_returns_200_for_unhandled_event(self, app):
        event = MagicMock()
        event.event = "track_published"
        event.room = MagicMock()
        event.participant = MagicMock()

        with patch(
            "app.api.v1.webhooks._get_webhook_receiver"
        ) as mock_get_receiver:
            receiver = MagicMock()
            receiver.receive.return_value = event
            mock_get_receiver.return_value = receiver

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/interviews/webhooks/livekit",
                    content='{"event": "track_published"}',
                    headers={"Authorization": "valid-token"},
                )

        assert response.status_code == 200
