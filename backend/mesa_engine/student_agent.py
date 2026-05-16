"""
Mesa StudentAgent - Behavioral Analysis Agent
Each student gets one agent that tracks behavior over time
"""

try:
    from mesa import Agent
except ImportError:
    Agent = object

from collections import deque
from typing import Dict, Any, List, Set
import time
import logging

logger = logging.getLogger(__name__)


class StudentAgent(Agent):
    """
    Mesa Agent representing one student's behavior over time
    
    Responsibilities:
    - Observe events from detection layer
    - Detect behavioral patterns
    - Calculate risk scores
    - Provide explanations
    """
    
    def __init__(self, unique_id: int, model, student_id: str):
        """
        Initialize student agent
        
        Args:
            unique_id: Mesa agent ID
            model: Mesa model instance
            student_id: Student identifier
        """
        super().__init__(unique_id, model)
        self.student_id = student_id
        
        # State
        self.behavior_state = "NORMAL"  # NORMAL, SUSPICIOUS, FLAGGED
        self.risk_score = 0.0
        
        # Memory systems
        self.short_term_memory = deque(maxlen=30)  # Last 30 events (~30s at 1 event/sec)
        self.long_term_memory = deque(maxlen=3600)  # Cap at ~1 hour of events
        
        # Tracking
        self.confidence_tracker = 1.0
        self.violation_count = 0
        self.last_violation_time = None
        
        # Pattern detection
        self.patterns_detected: Set[str] = set()
        
        # Statistics
        self.total_events = 0
        self.session_start_time = time.time()
        
        logger.info(f"StudentAgent created for {student_id}")
    
    def observe(self, event: Dict[str, Any]):
        """
        Ingest a new event from detection layer
        
        Args:
            event: Event dictionary from event schema
        """
        # Add to memory
        self.short_term_memory.append(event)
        self.long_term_memory.append(event)
        self.total_events += 1
        
        # Analyze patterns
        self._detect_patterns()
        
        # Update risk
        self._update_risk(event)
        
        # Update state
        self._update_behavior_state()
    
    def _detect_patterns(self):
        """
        Pattern detection over short-term memory
        Identifies behavioral patterns that indicate cheating
        """
        if len(self.short_term_memory) < 5:
            return
        
        recent = list(self.short_term_memory)[-10:]
        
        # Clear old patterns (re-evaluate each time)
        self.patterns_detected.clear()
        
        # Pattern 1: Sustained gaze aversion
        gaze_away_count = sum(
            1 for e in recent 
            if e.get('event_type') == 'frame_analysis' 
            and e.get('gaze_direction') in ['away', 'left', 'right']
        )
        if gaze_away_count >= 7:
            self.patterns_detected.add("sustained_gaze_away")
        
        # Pattern 2: Excessive head movement
        head_angles = [
            e.get('head_angle', 0) 
            for e in recent 
            if e.get('event_type') == 'frame_analysis'
        ]
        if head_angles and (max(head_angles) - min(head_angles)) > 60:
            self.patterns_detected.add("excessive_head_movement")
        
        # Pattern 3: Phone + looking down combo (HIGH RISK)
        phone_down_count = sum(
            1 for e in recent 
            if e.get('event_type') == 'frame_analysis'
            and e.get('phone_detected') 
            and e.get('looking_down')
        )
        if phone_down_count >= 3:
            self.patterns_detected.add("phone_cheating_pattern")
        
        # Pattern 4: Sudden camera motion
        motions = [
            e.get('camera_motion') 
            for e in recent 
            if e.get('event_type') == 'frame_analysis'
        ]
        if motions.count('sudden') >= 3:
            self.patterns_detected.add("camera_manipulation")
        
        # Pattern 5: Face disappearance pattern
        face_absent_count = sum(
            1 for e in recent 
            if e.get('event_type') == 'frame_analysis'
            and not e.get('face_visible', True)
        )
        if face_absent_count >= 5:
            self.patterns_detected.add("sustained_face_absence")
        
        # Pattern 6: Multiple faces pattern
        multi_face_count = sum(
            1 for e in recent 
            if e.get('event_type') == 'frame_analysis'
            and e.get('face_count', 0) > 1
        )
        if multi_face_count >= 3:
            self.patterns_detected.add("multiple_people_present")
        
        # Pattern 7: Browser event clustering
        browser_events = [
            e for e in recent 
            if e.get('event_type') == 'browser_event'
        ]
        if len(browser_events) >= 3:
            self.patterns_detected.add("frequent_browser_violations")
    
    def _update_risk(self, event: Dict[str, Any]):
        """
        Update risk score based on event and patterns
        
        Uses formula: risk = base_risk × confidence × persistence × context
        """
        # Base risk from event
        base_risk = event.get('raw_risk', 0.0)
        
        # Confidence factor (from detection confidence)
        confidence_factor = event.get('confidence', 100.0) / 100.0
        
        # Persistence factor (increases if violations sustained)
        persistence_factor = 1.0
        if self.last_violation_time:
            time_since = time.time() - self.last_violation_time
            if time_since < 30:  # Within 30s
                persistence_factor = 1.5
            elif time_since < 60:  # Within 1 min
                persistence_factor = 1.2
        
        # Context factor (patterns multiply risk)
        context_factor = 1.0 + (len(self.patterns_detected) * 0.3)
        
        # Special high-risk patterns
        if "phone_cheating_pattern" in self.patterns_detected:
            context_factor *= 1.5
        if "multiple_people_present" in self.patterns_detected:
            context_factor *= 1.3
        
        # Final risk calculation
        calculated_risk = (
            base_risk 
            * confidence_factor 
            * persistence_factor 
            * context_factor
        )
        
        # Use exponential moving average for smoothing
        alpha = 0.3
        self.risk_score = alpha * calculated_risk + (1 - alpha) * self.risk_score
        
        # Cap at 100
        self.risk_score = min(self.risk_score, 100.0)
        
        # Update violation tracking
        if base_risk > 50:
            self.violation_count += 1
            self.last_violation_time = time.time()
    
    def _update_behavior_state(self):
        """
        Update behavior state based on risk score
        """
        if self.risk_score < 30:
            self.behavior_state = "NORMAL"
        elif self.risk_score < 70:
            self.behavior_state = "SUSPICIOUS"
        else:
            self.behavior_state = "FLAGGED"
    
    def get_explanation(self) -> Dict[str, Any]:
        """
        Generate human-readable explanation of current risk
        
        Returns:
            Dictionary with risk details and explanations
        """
        reasons = []
        
        # Pattern-based reasons
        pattern_explanations = {
            "sustained_gaze_away": "Student looked away from screen for extended period (7+ seconds)",
            "excessive_head_movement": "Unusual head movements detected (>60° range)",
            "phone_cheating_pattern": "Phone detected while looking down - potential cheating behavior",
            "camera_manipulation": "Suspicious camera movements detected",
            "sustained_face_absence": "Face not visible for extended period (5+ seconds)",
            "multiple_people_present": "Multiple people detected in frame",
            "frequent_browser_violations": "Multiple browser security violations (tab switch, copy/paste, etc.)"
        }
        
        for pattern in self.patterns_detected:
            if pattern in pattern_explanations:
                reasons.append(pattern_explanations[pattern])
        
        # Recent event-based reasons
        recent = list(self.short_term_memory)[-5:]
        
        # Check for objects
        if any(e.get('phone_detected') for e in recent):
            reasons.append("Mobile device visible in camera frame")
        if any(e.get('book_detected') for e in recent):
            reasons.append("Study materials (book) detected in frame")
        
        # Check for gestures
        if any(e.get('phone_call_gesture') for e in recent):
            reasons.append("Hand-to-ear gesture detected (possible phone call)")
        
        # Check for browser events
        browser_actions = [
            e.get('action') 
            for e in recent 
            if e.get('event_type') == 'browser_event'
        ]
        if browser_actions:
            reasons.append(f"Browser violations: {', '.join(set(browser_actions))}")
        
        return {
            "risk_score": round(self.risk_score, 2),
            "behavior_state": self.behavior_state,
            "confidence": round(self.confidence_tracker * 100, 1),
            "violation_count": self.violation_count,
            "patterns_detected": list(self.patterns_detected),
            "reasons": reasons,
            "timestamp": time.time(),
            "session_duration": round(time.time() - self.session_start_time, 1),
            "total_events": self.total_events
        }
    
    def get_risk_timeline(self, last_n: int = 30) -> List[Dict[str, Any]]:
        """
        Get risk timeline for visualization
        
        Args:
            last_n: Number of recent events to include
        
        Returns:
            List of timeline points
        """
        timeline = []
        events = list(self.long_term_memory)[-last_n:]
        
        for i, event in enumerate(events):
            timeline.append({
                "index": i,
                "timestamp": event.get('timestamp', 0),
                "risk": event.get('raw_risk', 0),
                "event_type": event.get('event_type', 'unknown')
            })
        
        return timeline
    
    def step(self):
        """
        Mesa step function (called each model step)
        Currently passive - agent reacts to events
        """
        pass
