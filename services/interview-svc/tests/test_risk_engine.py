"""Unit tests for the risk engine verdict determination and risk score aggregation."""

import json
import time
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from app.services.risk_engine import (
    ALPHA,
    MULTI_SIGNAL_BOOST,
    SIGNAL_WINDOW,
    THRESHOLDS,
    aggregate_risk_score,
    determine_verdict,
)


class TestDetermineVerdict:
    """Tests for determine_verdict function."""

    # --- Boundary values ---

    def test_score_zero_returns_safe(self):
        assert determine_verdict(0.0) == "SAFE"

    def test_score_just_below_mild_returns_safe(self):
        assert determine_verdict(29.99) == "SAFE"

    def test_score_at_mild_boundary_returns_mild(self):
        assert determine_verdict(30.0) == "MILD"

    def test_score_just_below_high_returns_mild(self):
        assert determine_verdict(49.99) == "MILD"

    def test_score_at_high_boundary_returns_high(self):
        assert determine_verdict(50.0) == "HIGH"

    def test_score_just_below_critical_returns_high(self):
        assert determine_verdict(79.99) == "HIGH"

    def test_score_at_critical_boundary_returns_critical(self):
        assert determine_verdict(80.0) == "CRITICAL"

    def test_score_100_returns_critical(self):
        assert determine_verdict(100.0) == "CRITICAL"

    # --- Clamping ---

    def test_negative_score_clamped_to_safe(self):
        assert determine_verdict(-10.0) == "SAFE"

    def test_score_above_100_clamped_to_critical(self):
        assert determine_verdict(150.0) == "CRITICAL"

    # --- Mid-range values ---

    def test_mid_safe_range(self):
        assert determine_verdict(15.0) == "SAFE"

    def test_mid_mild_range(self):
        assert determine_verdict(40.0) == "MILD"

    def test_mid_high_range(self):
        assert determine_verdict(65.0) == "HIGH"

    def test_mid_critical_range(self):
        assert determine_verdict(90.0) == "CRITICAL"


class TestThresholdsConstant:
    """Tests for the THRESHOLDS constant."""

    def test_thresholds_has_all_verdicts(self):
        assert set(THRESHOLDS.keys()) == {"SAFE", "MILD", "HIGH", "CRITICAL"}

    def test_thresholds_are_monotonically_increasing(self):
        values = [THRESHOLDS["SAFE"], THRESHOLDS["MILD"], THRESHOLDS["HIGH"], THRESHOLDS["CRITICAL"]]
        assert values == sorted(values)
        # Strictly increasing
        for i in range(len(values) - 1):
            assert values[i] < values[i + 1]


class TestAggregationConstants:
    """Tests for the risk aggregation constants."""

    def test_alpha_value(self):
        assert ALPHA == 0.3

    def test_signal_window_value(self):
        assert SIGNAL_WINDOW == 30

    def test_multi_signal_boost_value(self):
        assert MULTI_SIGNAL_BOOST == 0.1


class FakeRedis:
    """In-memory fake Redis for testing aggregate_risk_score without a real Redis server."""

    def __init__(self):
        self._hashes: dict[str, dict[str, str]] = {}
        self._strings: dict[str, str] = {}

    async def hgetall(self, key: str) -> dict[str, str]:
        return dict(self._hashes.get(key, {}))

    async def hset(self, key: str, field: str, value: str) -> None:
        if key not in self._hashes:
            self._hashes[key] = {}
        self._hashes[key][field] = value

    async def set(self, key: str, value: str) -> None:
        self._strings[key] = value

    async def get(self, key: str) -> str | None:
        return self._strings.get(key)


@pytest.fixture
def fake_redis():
    return FakeRedis()


@pytest.mark.asyncio
class TestAggregateRiskScore:
    """Tests for aggregate_risk_score function."""

    async def test_single_signal_returns_score_directly(self, fake_redis):
        """A single signal with no history should return the score itself (base = max*0.6 + avg*0.4 = score*1.0, boost=1)."""
        result = await aggregate_risk_score("session-1", "TAB_SWITCH", 50.0, fake_redis)
        # Single signal: base = 50*0.6 + 50*0.4 = 50, boost = 1 + (1-1)*0.1 = 1
        assert result == 50.0

    async def test_ema_smoothing_applied(self, fake_redis):
        """Second call to same signal should apply EMA smoothing."""
        await aggregate_risk_score("session-1", "TAB_SWITCH", 100.0, fake_redis)
        result = await aggregate_risk_score("session-1", "TAB_SWITCH", 0.0, fake_redis)
        # EMA: smoothed = 0.3 * 0 + 0.7 * 100 = 70
        # Single active signal (70 > 10): base = 70*0.6 + 70*0.4 = 70, boost = 1
        assert result == 70.0

    async def test_ema_smoothing_converges(self, fake_redis):
        """Repeated constant value should converge to that value."""
        target = 60.0
        for _ in range(20):
            result = await aggregate_risk_score("session-1", "GAZE_AWAY", target, fake_redis)
        # After many iterations, should converge to target
        assert abs(result - target) < 2.0

    async def test_multi_signal_boost(self, fake_redis):
        """Multiple active signals should apply boost."""
        await aggregate_risk_score("session-1", "TAB_SWITCH", 50.0, fake_redis)
        result = await aggregate_risk_score("session-1", "GAZE_AWAY", 50.0, fake_redis)
        # Two signals both at 50: max=50, avg=50, base=50*0.6+50*0.4=50
        # boost = 1 + (2-1)*0.1 = 1.1
        # final = 50 * 1.1 = 55.0
        assert result == pytest.approx(55.0)

    async def test_result_never_exceeds_100(self, fake_redis):
        """Final score should be capped at 100."""
        # Add many high-scoring signals to try to exceed 100
        for i in range(10):
            result = await aggregate_risk_score(
                "session-1", f"SIGNAL_{i}", 100.0, fake_redis
            )
        assert result <= 100.0

    async def test_low_score_signal_excluded_from_active(self, fake_redis):
        """Signals with score <= 10 should not be considered active."""
        await aggregate_risk_score("session-1", "TAB_SWITCH", 50.0, fake_redis)
        # Add a very low signal
        result = await aggregate_risk_score("session-1", "GAZE_AWAY", 5.0, fake_redis)
        # GAZE_AWAY score is 5 (<=10), so only TAB_SWITCH is active
        # Single active signal at 50: base = 50, boost = 1
        assert result == 50.0

    async def test_expired_signal_excluded(self, fake_redis):
        """Signals older than SIGNAL_WINDOW should be excluded."""
        # Manually insert an old signal
        old_time = time.time() - SIGNAL_WINDOW - 1
        old_data = json.dumps({"score": 80.0, "last_seen": old_time})
        await fake_redis.hset("cheat:signals:session-1", "OLD_SIGNAL", old_data)

        # Add a new signal
        result = await aggregate_risk_score("session-1", "TAB_SWITCH", 40.0, fake_redis)
        # OLD_SIGNAL is expired, only TAB_SWITCH (40) is active
        # base = 40*0.6 + 40*0.4 = 40, boost = 1
        assert result == 40.0

    async def test_no_active_signals_returns_zero(self, fake_redis):
        """If the new signal score is <= 10 and no other active signals, return 0."""
        result = await aggregate_risk_score("session-1", "TAB_SWITCH", 5.0, fake_redis)
        # Score 5 <= 10, so no active signals
        assert result == 0.0

    async def test_redis_failure_returns_raw_score(self):
        """If Redis is unavailable, should return the raw new_score as fallback."""
        broken_redis = AsyncMock()
        broken_redis.hgetall.side_effect = ConnectionError("Redis unavailable")

        result = await aggregate_risk_score("session-1", "TAB_SWITCH", 75.0, broken_redis)
        assert result == 75.0

    async def test_redis_failure_clamps_fallback(self):
        """Fallback should clamp score to [0, 100]."""
        broken_redis = AsyncMock()
        broken_redis.hgetall.side_effect = ConnectionError("Redis unavailable")

        result = await aggregate_risk_score("session-1", "TAB_SWITCH", 150.0, broken_redis)
        assert result == 100.0

        result = await aggregate_risk_score("session-1", "TAB_SWITCH", -10.0, broken_redis)
        assert result == 0.0

    async def test_stores_final_score_in_redis(self, fake_redis):
        """Should store the final aggregated score in Redis."""
        await aggregate_risk_score("session-1", "TAB_SWITCH", 60.0, fake_redis)
        stored = await fake_redis.get("cheat:risk:session-1")
        assert stored is not None
        assert float(stored) == 60.0

    async def test_aggregation_formula_with_three_signals(self, fake_redis):
        """Test the full formula with 3 active signals."""
        await aggregate_risk_score("session-1", "TAB_SWITCH", 80.0, fake_redis)
        await aggregate_risk_score("session-1", "GAZE_AWAY", 60.0, fake_redis)
        result = await aggregate_risk_score("session-1", "DEVTOOLS_OPEN", 40.0, fake_redis)
        # Active signals: TAB_SWITCH=80, GAZE_AWAY=60, DEVTOOLS_OPEN=40
        # max=80, avg=(80+60+40)/3=60
        # base = 80*0.6 + 60*0.4 = 48 + 24 = 72
        # boost = 1 + (3-1)*0.1 = 1.2
        # final = 72 * 1.2 = 86.4
        assert result == pytest.approx(86.4)
