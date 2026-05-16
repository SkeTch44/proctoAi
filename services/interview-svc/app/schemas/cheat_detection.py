from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AlertType(str, Enum):
    """Enumeration of all detectable cheating behaviors."""

    # Video-based
    MULTIPLE_FACES = "MULTIPLE_FACES"
    NO_FACE = "NO_FACE"
    GAZE_AWAY = "GAZE_AWAY"
    PHONE_DETECTED = "PHONE_DETECTED"
    BOOK_DETECTED = "BOOK_DETECTED"

    # Browser-based
    TAB_SWITCH = "TAB_SWITCH"
    COPY_DETECTED = "COPY_DETECTED"
    PASTE_DETECTED = "PASTE_DETECTED"
    DEVTOOLS_OPEN = "DEVTOOLS_OPEN"
    FULLSCREEN_EXIT = "FULLSCREEN_EXIT"

    # Audio-based
    MULTIPLE_SPEAKERS = "MULTIPLE_SPEAKERS"
    WHISPER_DETECTED = "WHISPER_DETECTED"

    # Composite
    SUSPICIOUS_PATTERN = "SUSPICIOUS_PATTERN"


class Severity(str, Enum):
    """Alert severity levels."""

    MILD = "MILD"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Verdict(str, Enum):
    """Risk score verdict classifications."""

    SAFE = "SAFE"
    MILD = "MILD"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class CheatDetectionResult(BaseModel):
    """Result from a single detection cycle."""

    suspicious: bool
    score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    verdict: str
    alert_type: str
    signals: dict[str, float]
    should_alert: bool
    details: dict


class RiskSummary(BaseModel):
    """Aggregated risk summary for a session."""

    session_id: str
    current_score: float
    current_verdict: str
    total_alerts: int
    alerts_by_severity: dict[str, int]
    alerts_by_type: dict[str, int]
    monitoring_duration_seconds: float
    frames_processed: int
    events_processed: int
    top_signals: list[dict]


# Browser event types that can be reported by the BrowserMonitor
BROWSER_EVENT_TYPES = {
    AlertType.TAB_SWITCH,
    AlertType.COPY_DETECTED,
    AlertType.PASTE_DETECTED,
    AlertType.DEVTOOLS_OPEN,
    AlertType.FULLSCREEN_EXIT,
}


class CheatEventRequest(BaseModel):
    """Request body for reporting a browser cheat event."""

    event_type: str
    details: dict
    timestamp: str

    @classmethod
    def validate_event_type(cls, v: str) -> str:
        """Validate that event_type is a valid browser event."""
        valid_types = {t.value for t in BROWSER_EVENT_TYPES}
        if v not in valid_types:
            raise ValueError(
                f"event_type must be one of {sorted(valid_types)}, got '{v}'"
            )
        return v


class CheatAlertResponse(BaseModel):
    """Response model for a cheat alert record."""

    id: str
    session_id: str
    alert_type: str
    severity: str
    score: float
    confidence: float
    details: Optional[dict] = None
    created_at: datetime
    acknowledged: bool

    class Config:
        from_attributes = True
