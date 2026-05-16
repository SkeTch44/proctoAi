"""
Proctoring Service API — /api/v1/proctoring/*

Handles:
  - Frame ingestion + full CheatDetector analysis (YOLO + gaze + phone/book)
  - Proctoring event logging
  - Risk score updates
  - Works for ALL session kinds: exam, interview, coding
"""

import base64
import logging
import sys
import os
from typing import Optional

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.config import get_settings

# Add project root so we can import the monolith's CheatDetector
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

logger = logging.getLogger("proctoring-svc")
router = APIRouter(prefix="/api/v1/proctoring", tags=["proctoring"])

# Singleton CheatDetector instance (lazy loaded)
_cheat_detector = None
# Singleton MesaService (lazy loaded)
_mesa_service = None


def _get_detector():
    global _cheat_detector
    if _cheat_detector is None:
        from backend.models.cheat_detector import CheatDetector
        _cheat_detector = CheatDetector()
        logger.info("CheatDetector loaded (YOLO + Gaze + Audio + CopyPaste)")
    return _cheat_detector


def _get_mesa():
    """Get or create the Mesa ABM service for behavioral pattern detection."""
    global _mesa_service
    if _mesa_service is None:
        try:
            from backend.services.mesa_service import MesaService
            _mesa_service = MesaService()
            _mesa_service.start()
            logger.info("MesaService started (ABM behavioral analysis)")
        except Exception as e:
            logger.warning(f"MesaService unavailable: {e}")
    return _mesa_service


class FrameRequest(BaseModel):
    session_id: str
    session_kind: str = "exam"  # exam | interview | coding
    frame_data: str  # base64 JPEG
    audio_data: Optional[list] = None
    timestamp: str


class FrameResponse(BaseModel):
    processed: bool
    suspicious: bool = False
    suspicion_score: float = 0
    verdict: str = "SAFE"
    alert_type: str = "NONE"
    face_count: int = 0
    phone_detected: bool = False
    book_detected: bool = False
    looking_away: bool = False
    details: dict = {}


class EventRequest(BaseModel):
    session_id: str
    session_kind: str = "exam"
    event_type: str  # tab_switch, copy, paste, fullscreen_exit, devtools_open
    severity: str = "low"
    details: str = ""
    content: str = ""  # For copy/paste events
    timestamp: str


class EventResponse(BaseModel):
    message: str
    suspicious: bool = False
    score: float = 0
    alert_type: str = ""


# ------------------------------------------------------------------ #
# POST /frame — full cheat detection on a proctoring frame
# ------------------------------------------------------------------ #
@router.post("/frame", response_model=FrameResponse)
def process_frame(body: FrameRequest):
    """
    Process a proctoring frame through the full CheatDetector pipeline:
      - YOLO: face count, phone detection, book detection
      - Gaze estimation: looking away
      - Temporal smoothing + certainty engine
      - Works for exam, interview, and coding sessions
    """
    detector = _get_detector()

    result = detector.analyze_frame(
        frame_data=body.frame_data,
        session_id=body.session_id,
    )

    if "error" in result and not result.get("suspicious"):
        # Frame decode failed or OpenCV missing
        return FrameResponse(processed=False, details={"error": result.get("error")})

    # Also analyze audio if provided
    audio_result = {}
    if body.audio_data and len(body.audio_data) > 0:
        try:
            audio_array = np.array(body.audio_data, dtype=np.float32)
            audio_result = detector.analyze_audio(audio_array, body.session_id)
        except Exception as e:
            logger.debug(f"Audio analysis skipped: {e}")

    # Feed result into Mesa ABM for temporal pattern detection
    mesa = _get_mesa()
    mesa_decision = None
    if mesa:
        try:
            mesa_event = {
                "event_type": "frame_analysis",
                "student_id": body.session_id,
                "session_kind": body.session_kind,
                "raw_risk": result.get("suspicion_score", 0),
                "confidence": result.get("confidence", 0) * 100,
                "face_count": result.get("face_count", 0),
                "face_visible": result.get("face_count", 0) > 0,
                "phone_detected": result.get("phone_detected", False),
                "book_detected": result.get("book_detected", False),
                "looking_down": result.get("looking_away", False),
                "gaze_direction": "away" if result.get("looking_away") else "center",
                "timestamp": body.timestamp,
            }
            agent = mesa.model.get_student_agent(body.session_id)
            agent.observe(mesa_event)
            mesa.model.step()

            from backend.risk_engine.decision_maker import DecisionMaker
            dm = DecisionMaker()
            mesa_decision = dm.make_decision(agent)
        except Exception as e:
            logger.debug(f"Mesa ABM feed skipped: {e}")

    return FrameResponse(
        processed=True,
        suspicious=result.get("suspicious", False),
        suspicion_score=result.get("suspicion_score", 0),
        verdict=mesa_decision["state"] if mesa_decision else result.get("verdict", "SAFE"),
        alert_type=result.get("alert_type", "NONE"),
        face_count=result.get("face_count", 0),
        phone_detected=result.get("phone_detected", False),
        book_detected=result.get("book_detected", False),
        looking_away=result.get("looking_away", False),
        details={
            "signals": result.get("signals", {}),
            "confidence": result.get("confidence", 0),
            "audio": audio_result,
            "mesa_patterns": mesa_decision["explanation"]["patterns_detected"] if mesa_decision else [],
            "mesa_risk": mesa_decision["risk_score"] if mesa_decision else 0,
            "mesa_reasons": mesa_decision["explanation"]["reasons"] if mesa_decision else [],
        },
    )


# ------------------------------------------------------------------ #
# POST /event — log a proctoring event (tab switch, copy, paste, etc.)
# ------------------------------------------------------------------ #
@router.post("/event", response_model=EventResponse)
def log_event(body: EventRequest):
    """
    Log a proctoring event and run cheat detection on it.
    Also feeds into Mesa ABM for temporal pattern detection.
    Supports: tab_switch, copy, paste, fullscreen_exit, devtools_open
    """
    detector = _get_detector()
    result = {"suspicious": False, "score": 0, "alert_type": body.event_type.upper()}

    if body.event_type == "tab_switch":
        result = detector.handle_tab_switch(body.session_id, body.details)
    elif body.event_type == "copy":
        result = detector.handle_copy(body.session_id, body.content or body.details)
    elif body.event_type == "paste":
        result = detector.handle_paste(body.session_id, body.content or body.details)
    elif body.event_type == "fullscreen_exit":
        result = {"suspicious": True, "score": 60, "alert_type": "FULLSCREEN_EXIT"}
    elif body.event_type == "devtools_open":
        result = {"suspicious": True, "score": 80, "alert_type": "DEVTOOLS_OPEN"}
    else:
        logger.info(f"[{body.session_id}] event={body.event_type} severity={body.severity}")

    # Feed into Mesa ABM
    mesa = _get_mesa()
    if mesa:
        try:
            mesa_event = {
                "event_type": "browser_event",
                "student_id": body.session_id,
                "session_kind": body.session_kind,
                "action": body.event_type,
                "raw_risk": result.get("score", 0),
                "confidence": 100,
                "timestamp": body.timestamp,
            }
            agent = mesa.model.get_student_agent(body.session_id)
            agent.observe(mesa_event)
        except Exception as e:
            logger.debug(f"Mesa event feed skipped: {e}")

    return EventResponse(
        message="Event processed",
        suspicious=result.get("suspicious", False),
        score=result.get("score", 0),
        alert_type=result.get("alert_type", body.event_type.upper()),
    )
