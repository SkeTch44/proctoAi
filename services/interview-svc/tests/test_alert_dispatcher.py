"""Unit tests for the AlertDispatcher service."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.alert_dispatcher import AlertDispatcher


@pytest.fixture
def mock_livekit():
    """Create a mock LiveKitAdapter with an async send_data method."""
    adapter = MagicMock()
    adapter.send_data = AsyncMock()
    return adapter


@pytest.fixture
def dispatcher(mock_livekit):
    """Create an AlertDispatcher with a mocked LiveKitAdapter."""
    return AlertDispatcher(livekit_adapter=mock_livekit)


def _make_alert(
    alert_id="alert-123",
    alert_type="TAB_SWITCH",
    severity="HIGH",
    score=65.0,
    confidence=0.9,
    details=None,
    created_at=None,
):
    """Create a mock CheatAlert object."""
    alert = MagicMock()
    alert.id = alert_id
    alert.alert_type = alert_type
    alert.severity = severity
    alert.score = score
    alert.confidence = confidence
    alert.details = details or {"count": 3}
    alert.created_at = created_at or datetime(2025, 1, 15, 10, 30, 0)
    return alert


def _make_risk_summary(
    session_id="session-abc",
    current_score=45.0,
    current_verdict="MILD",
    total_alerts=5,
    top_signals=None,
):
    """Create a mock RiskSummary object."""
    summary = MagicMock()
    summary.session_id = session_id
    summary.current_score = current_score
    summary.current_verdict = current_verdict
    summary.total_alerts = total_alerts
    summary.top_signals = top_signals or [{"signal": "TAB_SWITCH", "score": 40.0}]
    return summary


@pytest.mark.asyncio
class TestDispatchAlert:
    """Tests for dispatch_alert method."""

    async def test_sends_correct_payload(self, dispatcher, mock_livekit):
        alert = _make_alert()
        await dispatcher.dispatch_alert("session-abc", "room-xyz", alert)

        mock_livekit.send_data.assert_called_once()
        call_kwargs = mock_livekit.send_data.call_args[1]
        assert call_kwargs["room_name"] == "room-xyz"

        payload = json.loads(call_kwargs["data"])
        assert payload["type"] == "cheat_alert"
        assert payload["alert_id"] == "alert-123"
        assert payload["alert_type"] == "TAB_SWITCH"
        assert payload["severity"] == "HIGH"
        assert payload["score"] == 65.0
        assert payload["confidence"] == 0.9
        assert payload["details"] == {"count": 3}
        assert payload["session_id"] == "session-abc"
        assert payload["timestamp"] == "2025-01-15T10:30:00"

    async def test_handles_string_timestamp(self, dispatcher, mock_livekit):
        alert = _make_alert(created_at="2025-01-15T10:30:00Z")
        await dispatcher.dispatch_alert("session-abc", "room-xyz", alert)

        payload = json.loads(mock_livekit.send_data.call_args[1]["data"])
        assert payload["timestamp"] == "2025-01-15T10:30:00Z"

    async def test_does_not_raise_on_send_failure(self, dispatcher, mock_livekit):
        mock_livekit.send_data.side_effect = Exception("LiveKit unavailable")
        alert = _make_alert()

        # Should not raise
        await dispatcher.dispatch_alert("session-abc", "room-xyz", alert)

    async def test_sends_to_correct_room(self, dispatcher, mock_livekit):
        alert = _make_alert()
        await dispatcher.dispatch_alert("session-abc", "specific-room", alert)

        call_kwargs = mock_livekit.send_data.call_args[1]
        assert call_kwargs["room_name"] == "specific-room"


@pytest.mark.asyncio
class TestDispatchRiskUpdate:
    """Tests for dispatch_risk_update method."""

    async def test_sends_correct_payload(self, dispatcher, mock_livekit):
        summary = _make_risk_summary()
        await dispatcher.dispatch_risk_update("session-abc", "room-xyz", summary)

        mock_livekit.send_data.assert_called_once()
        call_kwargs = mock_livekit.send_data.call_args[1]
        assert call_kwargs["room_name"] == "room-xyz"

        payload = json.loads(call_kwargs["data"])
        assert payload["type"] == "risk_update"
        assert payload["session_id"] == "session-abc"
        assert payload["current_score"] == 45.0
        assert payload["current_verdict"] == "MILD"
        assert payload["total_alerts"] == 5
        assert payload["top_signals"] == [{"signal": "TAB_SWITCH", "score": 40.0}]

    async def test_does_not_raise_on_send_failure(self, dispatcher, mock_livekit):
        mock_livekit.send_data.side_effect = Exception("Connection reset")
        summary = _make_risk_summary()

        # Should not raise
        await dispatcher.dispatch_risk_update("session-abc", "room-xyz", summary)

    async def test_sends_to_correct_room(self, dispatcher, mock_livekit):
        summary = _make_risk_summary()
        await dispatcher.dispatch_risk_update("session-abc", "my-room", summary)

        call_kwargs = mock_livekit.send_data.call_args[1]
        assert call_kwargs["room_name"] == "my-room"


@pytest.mark.asyncio
class TestDispatchMonitoringStatus:
    """Tests for dispatch_monitoring_status method."""

    @pytest.mark.parametrize("status", ["started", "stopped", "paused", "degraded"])
    async def test_sends_correct_payload(self, dispatcher, mock_livekit, status):
        await dispatcher.dispatch_monitoring_status("session-abc", "room-xyz", status)

        mock_livekit.send_data.assert_called_once()
        call_kwargs = mock_livekit.send_data.call_args[1]
        assert call_kwargs["room_name"] == "room-xyz"

        payload = json.loads(call_kwargs["data"])
        assert payload["type"] == "monitoring_status"
        assert payload["session_id"] == "session-abc"
        assert payload["status"] == status

    async def test_does_not_raise_on_send_failure(self, dispatcher, mock_livekit):
        mock_livekit.send_data.side_effect = Exception("Timeout")

        # Should not raise
        await dispatcher.dispatch_monitoring_status("session-abc", "room-xyz", "started")

    async def test_sends_to_correct_room(self, dispatcher, mock_livekit):
        await dispatcher.dispatch_monitoring_status("session-abc", "target-room", "stopped")

        call_kwargs = mock_livekit.send_data.call_args[1]
        assert call_kwargs["room_name"] == "target-room"
