"""
Risk Engine - Verdict determination and risk score aggregation for interview cheat detection.

Maps aggregated risk scores to categorical severity verdicts using
fixed thresholds consistent with the existing DecisionMaker pattern.
Provides EMA-smoothed risk score aggregation across multiple detection signals.
"""

import json
import time
from typing import Literal

from redis.asyncio import Redis

Verdict = Literal["SAFE", "MILD", "HIGH", "CRITICAL"]

# Threshold boundaries for verdict classification.
# Each key maps to the lower bound (inclusive) of that verdict range.
# The ranges are: [0, 30) → SAFE, [30, 50) → MILD, [50, 80) → HIGH, [80, 100] → CRITICAL
THRESHOLDS: dict[str, float] = {
    "SAFE": 0.0,
    "MILD": 30.0,
    "HIGH": 50.0,
    "CRITICAL": 80.0,
}

# Risk score aggregation constants
ALPHA = 0.3  # EMA smoothing factor
SIGNAL_WINDOW = 30  # seconds to consider signals "active"
MULTI_SIGNAL_BOOST = 0.1  # 10% boost per additional active signal


def determine_verdict(risk_score: float) -> Verdict:
    """Classify a risk score into a severity verdict.

    The function is:
    - Deterministic: same input always produces the same output.
    - Monotonically non-decreasing: higher scores never produce lower-severity verdicts.
    - Bounded: only returns one of the 4 valid verdict strings.

    Scores outside [0, 100] are clamped to the nearest bound before classification.

    Args:
        risk_score: A numeric risk score. Values outside [0, 100] are clamped.

    Returns:
        One of "SAFE", "MILD", "HIGH", or "CRITICAL".
    """
    # Clamp to valid range
    clamped = max(0.0, min(100.0, risk_score))

    if clamped < THRESHOLDS["MILD"]:
        return "SAFE"
    if clamped < THRESHOLDS["HIGH"]:
        return "MILD"
    if clamped < THRESHOLDS["CRITICAL"]:
        return "HIGH"
    return "CRITICAL"


async def aggregate_risk_score(
    session_id: str,
    new_signal: str,
    new_score: float,
    redis_client: Redis,
) -> float:
    """Aggregate a new detection signal into the session's running risk score.

    Uses exponential moving average (EMA) smoothing per signal and combines
    active signals with a multi-signal boost factor.

    Algorithm:
        1. Retrieve signal history from Redis
        2. Apply EMA: smoothed = ALPHA * new_score + (1 - ALPHA) * prev_score
        3. Store updated signal with timestamp
        4. Collect active signals (within SIGNAL_WINDOW, score > 10)
        5. Calculate: base_score = max_score * 0.6 + avg_score * 0.4
        6. Apply boost: boost = 1 + (active_count - 1) * 0.1
        7. Final: min(100.0, base_score * boost)

    Args:
        session_id: The interview session identifier.
        new_signal: Name of the detection signal (e.g., "TAB_SWITCH", "GAZE_AWAY").
        new_score: Raw score for this signal, in range [0, 100].
        redis_client: An async Redis client instance.

    Returns:
        The aggregated risk score, always in [0, 100].
        Falls back to returning new_score if Redis is unavailable.
    """
    try:
        return await _aggregate_with_redis(session_id, new_signal, new_score, redis_client)
    except Exception:
        # Redis unavailable - return raw score as fallback
        return max(0.0, min(100.0, new_score))


async def _aggregate_with_redis(
    session_id: str,
    new_signal: str,
    new_score: float,
    redis_client: Redis,
) -> float:
    """Internal aggregation logic using Redis for state persistence."""
    redis_key = f"cheat:signals:{session_id}"
    now = time.time()

    # Step 1: Retrieve signal history from Redis
    signal_history_raw = await redis_client.hgetall(redis_key)

    # Parse existing signal data
    signal_history: dict[str, dict] = {}
    for key, value in signal_history_raw.items():
        # Redis returns bytes; decode if needed
        signal_name = key.decode() if isinstance(key, bytes) else key
        raw_value = value.decode() if isinstance(value, bytes) else value
        signal_history[signal_name] = json.loads(raw_value)

    # Step 2: Apply EMA smoothing for the new signal
    if new_signal in signal_history:
        prev_score = float(signal_history[new_signal]["score"])
        smoothed = ALPHA * new_score + (1 - ALPHA) * prev_score
    else:
        smoothed = float(new_score)

    # Step 3: Store updated signal with timestamp in Redis
    signal_data = json.dumps({"score": smoothed, "last_seen": now})
    await redis_client.hset(redis_key, new_signal, signal_data)

    # Update local history for aggregation
    signal_history[new_signal] = {"score": smoothed, "last_seen": now}

    # Step 4: Collect active signals (seen within SIGNAL_WINDOW, score > 10)
    active_signals: dict[str, float] = {}
    for signal_name, data in signal_history.items():
        if now - data["last_seen"] < SIGNAL_WINDOW and data["score"] > 10:
            active_signals[signal_name] = data["score"]

    # Step 5: Calculate aggregate score
    if not active_signals:
        final_score = 0.0
    else:
        max_score = max(active_signals.values())
        avg_score = sum(active_signals.values()) / len(active_signals)

        # Weighted combination: 60% max, 40% average
        base_score = max_score * 0.6 + avg_score * 0.4

        # Step 6: Multi-signal boost
        active_count = len(active_signals)
        boost = 1 + (active_count - 1) * MULTI_SIGNAL_BOOST

        # Step 7: Final score capped at 100
        final_score = min(100.0, base_score * boost)

    # Store final score in Redis
    await redis_client.set(f"cheat:risk:{session_id}", str(final_score))

    return final_score
