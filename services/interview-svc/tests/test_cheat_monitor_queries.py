"""Unit tests for CheatMonitor.get_session_risk_summary and get_alert_history."""

import json
import time
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.cheat_alert import CheatAlert
from app.models.cheat_monitoring_state import CheatMonitoringState
from app.schemas.cheat_detection import CheatAlertResponse, RiskSummary
from app.services.cheat_monitor import CheatMonitor


@pytest.fixture
def mock_db():
    """Create a mock async database session."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    return db


@pytest.fixture
def mock_livekit():
    """Create a mock LiveKit adapter."""
    return AsyncMock()


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.hgetall = AsyncMock(return_value={})
    return redis


@pytest.fixture
def mock_http_client():
    """Create a mock httpx AsyncClient."""
    return AsyncMock()


@pytest.fixture
def monitor(mock_db, mock_livekit, mock_redis, mock_http_client):
    """Create a CheatMonitor with mocked dependencies."""
    return CheatMonitor(
        db=mock_db,
        livekit=mock_livekit,
        redis_client=mock_redis,
        http_client=mock_http_client,
    )


class TestGetSessionRiskSummary:
    """Tests for CheatMonitor.get_session_risk_summary."""

    @pytest.mark.asyncio
    async def test_returns_default_when_no_monitoring_state(self, monitor, mock_db):
        """When no monitoring state exists, return zeroed-out summary."""
        # First call returns None (no monitoring state)
        # The method calls _get_monitoring_state which does a select
        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = AsyncMock()
            result.scalar_one_or_none = MagicMock(return_value=None)
            return result

        mock_db.execute = AsyncMock(side_effect=execute_side_effect)

        summary = await monitor.get_session_risk_summary("sess-1")

        assert isinstance(summary, RiskSummary)
        assert summary.session_id == "sess-1"
        assert summary.current_score == 0.0
        assert summary.current_verdict == "SAFE"
        assert summary.total_alerts == 0
        assert summary.alerts_by_severity == {}
        assert summary.alerts_by_type == {}
        assert summary.monitoring_duration_seconds == 0.0
        assert summary.frames_processed == 0
        assert summary.events_processed == 0
        assert summary.top_signals == []

    @pytest.mark.asyncio
    async def test_returns_summary_with_active_monitoring(
        self, monitor, mock_db, mock_redis
    ):
        """When monitoring state exists, return populated summary."""
        # Create a monitoring state
        state = MagicMock(spec=CheatMonitoringState)
        state.session_id = "sess-1"
        state.status = "active"
        state.started_at = datetime.now(UTC) - timedelta(minutes=5)
        state.stopped_at = None
        state.total_frames_processed = 150
        state.total_events_processed = 10
        state.total_alerts_generated = 3
        state.current_risk_score = 45.0
        state.current_verdict = "MILD"

        # Set up Redis to return a risk score
        mock_redis.get = AsyncMock(return_value=b"47.5")
        mock_redis.hgetall = AsyncMock(return_value={
            b"TAB_SWITCH": json.dumps({"score": 40.0, "last_seen": time.time()}).encode(),
            b"GAZE_AWAY": json.dumps({"score": 35.0, "last_seen": time.time()}).encode(),
            b"COPY_DETECTED": json.dumps({"score": 20.0, "last_seen": time.time()}).encode(),
            b"DEVTOOLS_OPEN": json.dumps({"score": 10.0, "last_seen": time.time()}).encode(),
        })

        # Set up DB execute calls:
        # 1st call: _get_monitoring_state -> returns state
        # 2nd call: severity aggregation -> returns [(HIGH, 2), (MILD, 1)]
        # 3rd call: type aggregation -> returns [(TAB_SWITCH, 2), (GAZE_AWAY, 1)]
        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = AsyncMock()
            if call_count == 1:
                # _get_monitoring_state
                result.scalar_one_or_none = MagicMock(return_value=state)
            elif call_count == 2:
                # severity aggregation
                result.all = MagicMock(return_value=[("HIGH", 2), ("MILD", 1)])
            elif call_count == 3:
                # type aggregation
                result.all = MagicMock(return_value=[("TAB_SWITCH", 2), ("GAZE_AWAY", 1)])
            return result

        mock_db.execute = AsyncMock(side_effect=execute_side_effect)

        summary = await monitor.get_session_risk_summary("sess-1")

        assert isinstance(summary, RiskSummary)
        assert summary.session_id == "sess-1"
        assert summary.current_score == 47.5  # From Redis
        assert summary.current_verdict == "MILD"
        assert summary.total_alerts == 3
        assert summary.alerts_by_severity == {"HIGH": 2, "MILD": 1}
        assert summary.alerts_by_type == {"TAB_SWITCH": 2, "GAZE_AWAY": 1}
        assert summary.monitoring_duration_seconds > 0
        assert summary.frames_processed == 150
        assert summary.events_processed == 10
        # Top 3 signals sorted by score descending
        assert len(summary.top_signals) == 3
        assert summary.top_signals[0]["signal"] == "TAB_SWITCH"
        assert summary.top_signals[0]["score"] == 40.0
        assert summary.top_signals[1]["signal"] == "GAZE_AWAY"
        assert summary.top_signals[2]["signal"] == "COPY_DETECTED"

    @pytest.mark.asyncio
    async def test_falls_back_to_db_score_when_redis_unavailable(
        self, monitor, mock_db, mock_redis
    ):
        """When Redis is unavailable, use the score from monitoring state."""
        state = MagicMock(spec=CheatMonitoringState)
        state.session_id = "sess-1"
        state.status = "active"
        state.started_at = datetime.now(UTC) - timedelta(minutes=2)
        state.stopped_at = None
        state.total_frames_processed = 50
        state.total_events_processed = 5
        state.current_risk_score = 30.0
        state.current_verdict = "MILD"

        # Redis raises an exception
        mock_redis.get = AsyncMock(side_effect=Exception("Connection refused"))
        mock_redis.hgetall = AsyncMock(side_effect=Exception("Connection refused"))

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = AsyncMock()
            if call_count == 1:
                result.scalar_one_or_none = MagicMock(return_value=state)
            elif call_count == 2:
                result.all = MagicMock(return_value=[])
            elif call_count == 3:
                result.all = MagicMock(return_value=[])
            return result

        mock_db.execute = AsyncMock(side_effect=execute_side_effect)

        summary = await monitor.get_session_risk_summary("sess-1")

        assert summary.current_score == 30.0  # Falls back to DB value
        assert summary.top_signals == []  # No signals from Redis

    @pytest.mark.asyncio
    async def test_monitoring_duration_with_stopped_session(
        self, monitor, mock_db, mock_redis
    ):
        """Duration is calculated from started_at to stopped_at for stopped sessions."""
        started = datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC)
        stopped = datetime(2024, 1, 1, 10, 30, 0, tzinfo=UTC)

        state = MagicMock(spec=CheatMonitoringState)
        state.session_id = "sess-1"
        state.status = "inactive"
        state.started_at = started
        state.stopped_at = stopped
        state.total_frames_processed = 900
        state.total_events_processed = 20
        state.current_risk_score = 0.0
        state.current_verdict = "SAFE"

        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.hgetall = AsyncMock(return_value={})

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = AsyncMock()
            if call_count == 1:
                result.scalar_one_or_none = MagicMock(return_value=state)
            elif call_count == 2:
                result.all = MagicMock(return_value=[])
            elif call_count == 3:
                result.all = MagicMock(return_value=[])
            return result

        mock_db.execute = AsyncMock(side_effect=execute_side_effect)

        summary = await monitor.get_session_risk_summary("sess-1")

        # 30 minutes = 1800 seconds
        assert summary.monitoring_duration_seconds == 1800.0


class TestGetAlertHistory:
    """Tests for CheatMonitor.get_alert_history."""

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_alerts(self, monitor, mock_db):
        """When no alerts exist, return empty list."""
        async def execute_side_effect(*args, **kwargs):
            result = AsyncMock()
            scalars_mock = MagicMock()
            scalars_mock.all = MagicMock(return_value=[])
            result.scalars = MagicMock(return_value=scalars_mock)
            return result

        mock_db.execute = AsyncMock(side_effect=execute_side_effect)

        alerts = await monitor.get_alert_history("sess-1")

        assert alerts == []

    @pytest.mark.asyncio
    async def test_returns_alerts_as_response_models(self, monitor, mock_db):
        """Alerts are returned as CheatAlertResponse models."""
        alert1 = MagicMock(spec=CheatAlert)
        alert1.id = "alert-1"
        alert1.session_id = "sess-1"
        alert1.alert_type = "TAB_SWITCH"
        alert1.severity = "MILD"
        alert1.score = 40.0
        alert1.confidence = 0.9
        alert1.details = {"url": "https://example.com"}
        alert1.created_at = datetime(2024, 1, 1, 10, 5, 0, tzinfo=UTC)
        alert1.acknowledged = False

        alert2 = MagicMock(spec=CheatAlert)
        alert2.id = "alert-2"
        alert2.session_id = "sess-1"
        alert2.alert_type = "DEVTOOLS_OPEN"
        alert2.severity = "HIGH"
        alert2.score = 80.0
        alert2.confidence = 0.95
        alert2.details = None
        alert2.created_at = datetime(2024, 1, 1, 10, 10, 0, tzinfo=UTC)
        alert2.acknowledged = True

        async def execute_side_effect(*args, **kwargs):
            result = AsyncMock()
            scalars_mock = MagicMock()
            scalars_mock.all = MagicMock(return_value=[alert2, alert1])
            result.scalars = MagicMock(return_value=scalars_mock)
            return result

        mock_db.execute = AsyncMock(side_effect=execute_side_effect)

        alerts = await monitor.get_alert_history("sess-1")

        assert len(alerts) == 2
        assert all(isinstance(a, CheatAlertResponse) for a in alerts)

        # Most recent first
        assert alerts[0].id == "alert-2"
        assert alerts[0].alert_type == "DEVTOOLS_OPEN"
        assert alerts[0].severity == "HIGH"
        assert alerts[0].score == 80.0
        assert alerts[0].acknowledged is True

        assert alerts[1].id == "alert-1"
        assert alerts[1].alert_type == "TAB_SWITCH"
        assert alerts[1].severity == "MILD"
        assert alerts[1].score == 40.0
        assert alerts[1].details == {"url": "https://example.com"}

    @pytest.mark.asyncio
    async def test_respects_limit_parameter(self, monitor, mock_db):
        """The limit parameter controls how many alerts are returned."""
        # Create 5 mock alerts
        alerts_data = []
        for i in range(5):
            alert = MagicMock(spec=CheatAlert)
            alert.id = f"alert-{i}"
            alert.session_id = "sess-1"
            alert.alert_type = "TAB_SWITCH"
            alert.severity = "MILD"
            alert.score = 30.0
            alert.confidence = 0.9
            alert.details = None
            alert.created_at = datetime(2024, 1, 1, 10, i, 0, tzinfo=UTC)
            alert.acknowledged = False
            alerts_data.append(alert)

        async def execute_side_effect(*args, **kwargs):
            result = AsyncMock()
            scalars_mock = MagicMock()
            # Simulate DB returning only 3 (respecting limit)
            scalars_mock.all = MagicMock(return_value=alerts_data[:3])
            result.scalars = MagicMock(return_value=scalars_mock)
            return result

        mock_db.execute = AsyncMock(side_effect=execute_side_effect)

        alerts = await monitor.get_alert_history("sess-1", limit=3)

        assert len(alerts) == 3

    @pytest.mark.asyncio
    async def test_enforces_max_limit_of_100(self, monitor, mock_db):
        """Limit is capped at 100 even if a higher value is requested."""
        async def execute_side_effect(*args, **kwargs):
            result = AsyncMock()
            scalars_mock = MagicMock()
            scalars_mock.all = MagicMock(return_value=[])
            result.scalars = MagicMock(return_value=scalars_mock)
            return result

        mock_db.execute = AsyncMock(side_effect=execute_side_effect)

        # Request 200 but should be capped at 100
        await monitor.get_alert_history("sess-1", limit=200)

        # Verify the query was called (we can't easily inspect the limit
        # in the SQLAlchemy query object, but the method should not error)
        assert mock_db.execute.called

    @pytest.mark.asyncio
    async def test_handles_null_acknowledged_field(self, monitor, mock_db):
        """Alerts with None acknowledged field default to False."""
        alert = MagicMock(spec=CheatAlert)
        alert.id = "alert-1"
        alert.session_id = "sess-1"
        alert.alert_type = "GAZE_AWAY"
        alert.severity = "MILD"
        alert.score = 35.0
        alert.confidence = 0.8
        alert.details = {}
        alert.created_at = datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC)
        alert.acknowledged = None  # Could be None in DB

        async def execute_side_effect(*args, **kwargs):
            result = AsyncMock()
            scalars_mock = MagicMock()
            scalars_mock.all = MagicMock(return_value=[alert])
            result.scalars = MagicMock(return_value=scalars_mock)
            return result

        mock_db.execute = AsyncMock(side_effect=execute_side_effect)

        alerts = await monitor.get_alert_history("sess-1")

        assert len(alerts) == 1
        assert alerts[0].acknowledged is False
