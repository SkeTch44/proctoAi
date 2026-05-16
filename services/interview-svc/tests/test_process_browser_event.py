"""Unit tests for CheatMonitor.process_browser_event method."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.models.cheat_monitoring_state import CheatMonitoringState
from app.models.interview_session import InterviewSession
from app.schemas.cheat_detection import CheatDetectionResult
from app.services.cheat_monitor import CheatMonitor


@pytest.fixture
def mock_db():
    """Create a mock async database session."""
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.fixture
def mock_livekit():
    """Create a mock LiveKit adapter."""
    livekit = AsyncMock()
    livekit.send_data = AsyncMock()
    return livekit


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    redis = AsyncMock()
    redis.set = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.delete = AsyncMock()
    redis.sadd = AsyncMock()
    redis.sismember = AsyncMock(return_value=False)
    redis.hgetall = AsyncMock(return_value={})
    redis.hset = AsyncMock()
    return redis


@pytest.fixture
def mock_http_client():
    """Create a mock httpx AsyncClient."""
    client = AsyncMock()
    return client


@pytest.fixture
def monitor(mock_db, mock_livekit, mock_redis, mock_http_client):
    """Create a CheatMonitor with mocked dependencies."""
    return CheatMonitor(
        db=mock_db,
        livekit=mock_livekit,
        redis_client=mock_redis,
        http_client=mock_http_client,
    )


def _make_session(session_id="sess-1", status="active", room_name="room-1"):
    """Helper to create a mock InterviewSession."""
    session = MagicMock(spec=InterviewSession)
    session.id = session_id
    session.status = status
    session.room_name = room_name
    return session


def _make_monitoring_state(session_id="sess-1", status="active"):
    """Helper to create a mock CheatMonitoringState."""
    state = MagicMock()
    state.session_id = session_id
    state.status = status
    state.total_events_processed = 0
    state.total_alerts_generated = 0
    state.total_frames_processed = 0
    state.current_risk_score = 0.0
    state.current_verdict = "SAFE"
    state.started_at = None
    state.stopped_at = None
    return state


def _setup_db_execute(mock_db, results_map):
    """Configure mock_db.execute to return different results based on call order."""
    call_results = iter(results_map)

    async def execute_side_effect(*args, **kwargs):
        result = AsyncMock()
        result.scalar_one_or_none = MagicMock(return_value=next(call_results))
        return result

    mock_db.execute = AsyncMock(side_effect=execute_side_effect)


class TestProcessBrowserEventInactiveMonitoring:
    """Tests for process_browser_event when monitoring is not active."""

    @pytest.mark.asyncio
    async def test_returns_neutral_when_no_monitoring_state(self, monitor, mock_db):
        """Returns neutral result when no monitoring state exists."""
        _setup_db_execute(mock_db, [None])

        result = await monitor.process_browser_event(
            session_id="sess-1",
            event_type="TAB_SWITCH",
            details={"reason": "visibilitychange"},
            timestamp="2024-01-01T00:00:00Z",
        )

        assert result.suspicious is False
        assert result.score == 0.0
        assert result.verdict == "SAFE"
        assert result.should_alert is False

    @pytest.mark.asyncio
    async def test_returns_neutral_when_monitoring_paused(self, monitor, mock_db):
        """Returns neutral result when monitoring is paused."""
        state = _make_monitoring_state(status="paused")
        _setup_db_execute(mock_db, [state])

        result = await monitor.process_browser_event(
            session_id="sess-1",
            event_type="DEVTOOLS_OPEN",
            details={},
            timestamp="2024-01-01T00:00:00Z",
        )

        assert result.suspicious is False
        assert result.score == 0.0
        assert result.verdict == "SAFE"
        assert result.should_alert is False

    @pytest.mark.asyncio
    async def test_returns_neutral_when_monitoring_inactive(self, monitor, mock_db):
        """Returns neutral result when monitoring is inactive."""
        state = _make_monitoring_state(status="inactive")
        _setup_db_execute(mock_db, [state])

        result = await monitor.process_browser_event(
            session_id="sess-1",
            event_type="TAB_SWITCH",
            details={},
            timestamp="2024-01-01T00:00:00Z",
        )

        assert result.suspicious is False
        assert result.verdict == "SAFE"


class TestProcessBrowserEventDeduplication:
    """Tests for event deduplication logic."""

    @pytest.mark.asyncio
    async def test_returns_cached_result_for_duplicate_event(self, monitor, mock_db, mock_redis):
        """Duplicate events return the cached result without re-processing."""
        state = _make_monitoring_state(status="active")
        _setup_db_execute(mock_db, [state])

        # Simulate that the event hash is already in the Redis set
        mock_redis.sismember = AsyncMock(return_value=True)

        # Simulate cached result
        cached_result = CheatDetectionResult(
            suspicious=True,
            score=40.0,
            confidence=0.9,
            verdict="MILD",
            alert_type="TAB_SWITCH",
            signals={"TAB_SWITCH": 40.0},
            should_alert=False,
            details={"reason": "visibilitychange"},
        )
        mock_redis.get = AsyncMock(
            return_value=cached_result.model_dump_json().encode()
        )

        result = await monitor.process_browser_event(
            session_id="sess-1",
            event_type="TAB_SWITCH",
            details={"reason": "visibilitychange"},
            timestamp="2024-01-01T00:00:00Z",
        )

        assert result.score == 40.0
        assert result.verdict == "MILD"
        assert result.alert_type == "TAB_SWITCH"
        # Should NOT have called the http_client (no forwarding to proctoring-svc)
        mock_db.commit.assert_not_called()


class TestProcessBrowserEventScoring:
    """Tests for event scoring and risk aggregation."""

    @pytest.mark.asyncio
    @patch("app.services.cheat_monitor.get_settings")
    async def test_devtools_open_gets_high_score(
        self, mock_settings, monitor, mock_db, mock_redis, mock_http_client
    ):
        """DEVTOOLS_OPEN event gets base score of 80."""
        mock_settings.return_value = MagicMock(PROCTORING_SVC_URL="http://proctoring:8001")

        state = _make_monitoring_state(status="active")
        session = _make_session()
        _setup_db_execute(mock_db, [state, state, session])

        # Proctoring-svc returns a score
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"suspicious": True, "score": 80, "alert_type": "DEVTOOLS_OPEN"}
        mock_http_client.post = AsyncMock(return_value=mock_response)

        result = await monitor.process_browser_event(
            session_id="sess-1",
            event_type="DEVTOOLS_OPEN",
            details={},
            timestamp="2024-01-01T00:00:00Z",
        )

        assert result.score == 80.0
        assert result.suspicious is True
        assert result.alert_type == "DEVTOOLS_OPEN"

    @pytest.mark.asyncio
    @patch("app.services.cheat_monitor.get_settings")
    async def test_tab_switch_gets_score_40(
        self, mock_settings, monitor, mock_db, mock_redis, mock_http_client
    ):
        """TAB_SWITCH event gets base score of 40."""
        mock_settings.return_value = MagicMock(PROCTORING_SVC_URL="http://proctoring:8001")

        state = _make_monitoring_state(status="active")
        _setup_db_execute(mock_db, [state, state])

        # Proctoring-svc returns a lower score
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"suspicious": True, "score": 30, "alert_type": "TAB_SWITCH"}
        mock_http_client.post = AsyncMock(return_value=mock_response)

        result = await monitor.process_browser_event(
            session_id="sess-1",
            event_type="TAB_SWITCH",
            details={"reason": "visibilitychange"},
            timestamp="2024-01-01T00:00:00Z",
        )

        # Should use the higher of proctoring score (30) and interview base (40)
        assert result.score == 40.0
        assert result.alert_type == "TAB_SWITCH"

    @pytest.mark.asyncio
    @patch("app.services.cheat_monitor.get_settings")
    async def test_copy_paste_gets_score_30(
        self, mock_settings, monitor, mock_db, mock_redis, mock_http_client
    ):
        """COPY_DETECTED event gets base score of 30."""
        mock_settings.return_value = MagicMock(PROCTORING_SVC_URL="http://proctoring:8001")

        state = _make_monitoring_state(status="active")
        _setup_db_execute(mock_db, [state, state])

        # Proctoring-svc returns 0 (no detection)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"suspicious": False, "score": 0, "alert_type": "COPY_DETECTED"}
        mock_http_client.post = AsyncMock(return_value=mock_response)

        result = await monitor.process_browser_event(
            session_id="sess-1",
            event_type="COPY_DETECTED",
            details={"content": "some text"},
            timestamp="2024-01-01T00:00:00Z",
        )

        # Should use interview base score of 30
        assert result.score == 30.0


class TestProcessBrowserEventProctoringFallback:
    """Tests for graceful handling of proctoring-svc unavailability."""

    @pytest.mark.asyncio
    @patch("app.services.cheat_monitor.get_settings")
    async def test_uses_local_scoring_on_timeout(
        self, mock_settings, monitor, mock_db, mock_redis, mock_http_client
    ):
        """Falls back to local scoring when proctoring-svc times out."""
        mock_settings.return_value = MagicMock(PROCTORING_SVC_URL="http://proctoring:8001")

        state = _make_monitoring_state(status="active")
        session = _make_session()
        # DEVTOOLS_OPEN with local score 80 will trigger alert (HIGH/CRITICAL)
        # Calls: get_monitoring_state, _create_and_persist_alert->get_monitoring_state, get_session
        _setup_db_execute(mock_db, [state, state, session])

        # Simulate timeout
        mock_http_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        result = await monitor.process_browser_event(
            session_id="sess-1",
            event_type="DEVTOOLS_OPEN",
            details={},
            timestamp="2024-01-01T00:00:00Z",
        )

        # Should use local fallback score for DEVTOOLS_OPEN (80)
        assert result.score == 80.0
        assert result.suspicious is True

    @pytest.mark.asyncio
    @patch("app.services.cheat_monitor.get_settings")
    async def test_uses_local_scoring_on_connection_error(
        self, mock_settings, monitor, mock_db, mock_redis, mock_http_client
    ):
        """Falls back to local scoring when proctoring-svc is unreachable."""
        mock_settings.return_value = MagicMock(PROCTORING_SVC_URL="http://proctoring:8001")

        state = _make_monitoring_state(status="active")
        _setup_db_execute(mock_db, [state, state])

        # Simulate connection error
        mock_http_client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))

        result = await monitor.process_browser_event(
            session_id="sess-1",
            event_type="TAB_SWITCH",
            details={},
            timestamp="2024-01-01T00:00:00Z",
        )

        # Should use local fallback score for TAB_SWITCH (40)
        assert result.score == 40.0

    @pytest.mark.asyncio
    @patch("app.services.cheat_monitor.get_settings")
    async def test_uses_local_scoring_on_5xx(
        self, mock_settings, monitor, mock_db, mock_redis, mock_http_client
    ):
        """Falls back to local scoring when proctoring-svc returns 5xx."""
        mock_settings.return_value = MagicMock(PROCTORING_SVC_URL="http://proctoring:8001")

        state = _make_monitoring_state(status="active")
        session = _make_session()
        # FULLSCREEN_EXIT with local score 60 may trigger alert depending on aggregation
        # Provide enough results: get_monitoring_state, _create_and_persist_alert->get_monitoring_state, get_session
        _setup_db_execute(mock_db, [state, state, session])

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_http_client.post = AsyncMock(return_value=mock_response)

        result = await monitor.process_browser_event(
            session_id="sess-1",
            event_type="FULLSCREEN_EXIT",
            details={},
            timestamp="2024-01-01T00:00:00Z",
        )

        # Should use local fallback score for FULLSCREEN_EXIT (60)
        assert result.score == 60.0


class TestProcessBrowserEventAlertGeneration:
    """Tests for alert creation and dispatch when thresholds are exceeded."""

    @pytest.mark.asyncio
    @patch("app.services.cheat_monitor.get_settings")
    @patch("app.services.cheat_monitor.aggregate_risk_score")
    @patch("app.services.cheat_monitor.determine_verdict")
    async def test_creates_alert_when_verdict_high(
        self,
        mock_verdict,
        mock_aggregate,
        mock_settings,
        monitor,
        mock_db,
        mock_redis,
        mock_http_client,
        mock_livekit,
    ):
        """Creates and dispatches alert when verdict is HIGH."""
        mock_settings.return_value = MagicMock(PROCTORING_SVC_URL="http://proctoring:8001")
        mock_aggregate.return_value = 60.0
        mock_verdict.return_value = "HIGH"

        state = _make_monitoring_state(status="active")
        session = _make_session()
        # Calls: get_monitoring_state, _create_and_persist_alert->get_monitoring_state, get_session
        _setup_db_execute(mock_db, [state, state, session])

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"suspicious": True, "score": 80, "alert_type": "DEVTOOLS_OPEN"}
        mock_http_client.post = AsyncMock(return_value=mock_response)

        result = await monitor.process_browser_event(
            session_id="sess-1",
            event_type="DEVTOOLS_OPEN",
            details={},
            timestamp="2024-01-01T00:00:00Z",
        )

        assert result.should_alert is True
        assert result.verdict == "HIGH"
        # Alert should have been added to the DB
        mock_db.add.assert_called()
        # LiveKit should have been called to dispatch alert
        mock_livekit.send_data.assert_called()

    @pytest.mark.asyncio
    @patch("app.services.cheat_monitor.get_settings")
    @patch("app.services.cheat_monitor.aggregate_risk_score")
    @patch("app.services.cheat_monitor.determine_verdict")
    async def test_no_alert_when_verdict_safe(
        self,
        mock_verdict,
        mock_aggregate,
        mock_settings,
        monitor,
        mock_db,
        mock_redis,
        mock_http_client,
        mock_livekit,
    ):
        """Does not create alert when verdict is SAFE."""
        mock_settings.return_value = MagicMock(PROCTORING_SVC_URL="http://proctoring:8001")
        mock_aggregate.return_value = 10.0
        mock_verdict.return_value = "SAFE"

        state = _make_monitoring_state(status="active")
        _setup_db_execute(mock_db, [state, state])

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"suspicious": False, "score": 10, "alert_type": "TAB_SWITCH"}
        mock_http_client.post = AsyncMock(return_value=mock_response)

        result = await monitor.process_browser_event(
            session_id="sess-1",
            event_type="TAB_SWITCH",
            details={},
            timestamp="2024-01-01T00:00:00Z",
        )

        assert result.should_alert is False
        assert result.verdict == "SAFE"
        # No alert should be added
        mock_db.add.assert_not_called()
        # No LiveKit dispatch
        mock_livekit.send_data.assert_not_called()


class TestProcessBrowserEventCounterUpdate:
    """Tests for monitoring state counter updates."""

    @pytest.mark.asyncio
    @patch("app.services.cheat_monitor.get_settings")
    @patch("app.services.cheat_monitor.aggregate_risk_score")
    @patch("app.services.cheat_monitor.determine_verdict")
    async def test_increments_event_count(
        self,
        mock_verdict,
        mock_aggregate,
        mock_settings,
        monitor,
        mock_db,
        mock_redis,
        mock_http_client,
    ):
        """Increments total_events_processed in monitoring state."""
        mock_settings.return_value = MagicMock(PROCTORING_SVC_URL="http://proctoring:8001")
        mock_aggregate.return_value = 20.0
        mock_verdict.return_value = "SAFE"

        state = _make_monitoring_state(status="active")
        state.total_events_processed = 5
        _setup_db_execute(mock_db, [state, state])

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"suspicious": False, "score": 10, "alert_type": "TAB_SWITCH"}
        mock_http_client.post = AsyncMock(return_value=mock_response)

        await monitor.process_browser_event(
            session_id="sess-1",
            event_type="TAB_SWITCH",
            details={},
            timestamp="2024-01-01T00:00:00Z",
        )

        assert state.total_events_processed == 6
        assert state.current_risk_score == 20.0
        assert state.current_verdict == "SAFE"
        mock_db.commit.assert_called()
