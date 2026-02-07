"""
Event Schema Definitions for Mesa ABM Integration
Defines structured event format for behavioral analysis
"""

from typing import Dict, Any, Literal
from dataclasses import dataclass, asdict
import time

# Event types
EventType = Literal[
    "frame_analysis",
    "browser_event", 
    "audio_event",
    "typing_event",
    "system_event"
]

# Gaze directions
GazeDirection = Literal["center", "left", "right", "up", "down", "away"]

# Camera motion types
CameraMotion = Literal["stable", "slight", "moderate", "sudden"]


@dataclass
class FrameAnalysisEvent:
    """
    Structured event from frame analysis
    Maps to Mesa StudentAgent.observe()
    """
    # Metadata
    student_id: str
    timestamp: float
    event_type: str = "frame_analysis"
    
    # Vision data
    face_visible: bool = False
    face_count: int = 0
    gaze_direction: GazeDirection = "center"
    
    # Advanced vision
    head_angle: float = 0.0  # Yaw
    head_pitch: float = 0.0
    looking_down: bool = False
    looking_away: bool = False
    
    # Hand gestures
    phone_call_gesture: bool = False
    camera_block_gesture: bool = False
    hand_count: int = 0
    
    # Objects
    phone_detected: bool = False
    book_detected: bool = False
    laptop_detected: bool = False
    
    # Motion
    camera_motion: CameraMotion = "stable"
    
    # Scores
    raw_risk: float = 0.0
    confidence: float = 100.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


@dataclass
class BrowserEvent:
    """Browser-side events"""
    student_id: str
    timestamp: float
    event_type: str = "browser_event"
    
    action: Literal[
        "tab_switch",
        "window_blur", 
        "fullscreen_exit",
        "screenshot",
        "copy",
        "paste",
        "right_click",
        "devtools_open"
    ] = "tab_switch"
    
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "MEDIUM"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AudioEvent:
    """Audio analysis events"""
    student_id: str
    timestamp: float
    event_type: str = "audio_event"
    
    volume_db: float = 0.0
    spike_detected: bool = False
    keyboard_sound_detected: bool = False
    keyboard_confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TypingEvent:
    """Typing pattern events"""
    student_id: str
    timestamp: float
    event_type: str = "typing_event"
    
    anomaly_type: Literal["paste", "slow_typing", "normal"] = "normal"
    avg_interval_ms: float = 0.0
    confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SystemEvent:
    """System monitoring events"""
    student_id: str
    timestamp: float
    event_type: str = "system_event"
    
    violation_type: Literal[
        "suspicious_process",
        "multiple_monitors",
        "vm_detected",
        "external_request"
    ] = "suspicious_process"
    
    details: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if data['details'] is None:
            data['details'] = {}
        return data


def create_frame_event(
    student_id: str,
    detection_result: Dict[str, Any],
    head_pose: Dict[str, Any],
    hand_gestures: Dict[str, Any],
    objects: list
) -> FrameAnalysisEvent:
    """
    Helper to create FrameAnalysisEvent from CheatDetector output
    """
    details = detection_result.get('details', {})
    smoothed = details.get('smoothed_scores', {})
    
    # Classify gaze direction
    gaze_score = smoothed.get('gaze_aversion', 0)
    if gaze_score < 20:
        gaze = "center"
    elif gaze_score < 40:
        gaze = "slight_away"
    else:
        gaze = "away"
    
    # Classify camera motion (placeholder - needs optical flow)
    camera_motion = "stable"
    
    return FrameAnalysisEvent(
        student_id=student_id,
        timestamp=time.time(),
        
        # Vision
        face_visible=details.get('faces_detected', 0) > 0,
        face_count=details.get('faces_detected', 0),
        gaze_direction=gaze,
        
        # Head pose
        head_angle=head_pose.get('yaw', 0.0),
        head_pitch=head_pose.get('pitch', 0.0),
        looking_down=head_pose.get('looking_down', False),
        looking_away=head_pose.get('looking_away', False),
        
        # Hands
        phone_call_gesture=hand_gestures.get('phone_call', False),
        camera_block_gesture=hand_gestures.get('camera_block', False),
        hand_count=hand_gestures.get('hand_count', 0),
        
        # Objects
        phone_detected=any(obj['class'] == 'cell phone' for obj in objects),
        book_detected=any(obj['class'] == 'book' for obj in objects),
        laptop_detected=any(obj['class'] == 'laptop' for obj in objects),
        
        # Motion
        camera_motion=camera_motion,
        
        # Scores
        raw_risk=detection_result.get('suspicion_score', 0.0),
        confidence=details.get('certainty', {}).get('certainty_score', 100.0)
    )
