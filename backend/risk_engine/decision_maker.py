"""
Decision Maker - Converts risk scores into actionable decisions
"""

from typing import Dict, Any, Literal
import logging

logger = logging.getLogger(__name__)

DecisionState = Literal["SAFE", "MILD", "HIGH", "CRITICAL"]


class DecisionMaker:
    """
    Converts risk scores from StudentAgent into actionable decisions
    
    IMPORTANT: No auto-fail in production (legal + fairness)
    Maximum action is "flag_for_review"
    """
    
    # Risk thresholds for decision states
    THRESHOLDS = {
        "SAFE": (0, 30),
        "MILD": (30, 50),
        "HIGH": (50, 80),
        "CRITICAL": (80, 100)
    }
    
    def __init__(self):
        """Initialize decision maker"""
        logger.info("DecisionMaker initialized")
    
    def make_decision(self, agent) -> Dict[str, Any]:
        """
        Determine action based on agent state
        
        Args:
            agent: StudentAgent instance
        
        Returns:
            Decision dictionary with action, notifications, and explanation
        """
        risk = agent.risk_score
        
        # Determine state
        state: DecisionState = "SAFE"
        for level, (low, high) in self.THRESHOLDS.items():
            if low <= risk < high:
                state = level
                break
        
        # Determine actions based on state
        actions = {
            "SAFE": {
                "action": "continue",
                "notify_student": False,
                "notify_supervisor": False,
                "log": False,
                "flag_for_review": False
            },
            "MILD": {
                "action": "continue",
                "notify_student": False,
                "notify_supervisor": False,
                "log": True,  # Log for later review
                "flag_for_review": False
            },
            "HIGH": {
                "action": "continue",  # Still continue, but alert
                "notify_student": True,  # Warn student
                "notify_supervisor": True,  # Alert supervisor
                "log": True,
                "flag_for_review": False
            },
            "CRITICAL": {
                "action": "flag_for_review",  # NO auto-fail, just flag
                "notify_student": True,
                "notify_supervisor": True,
                "log": True,
                "flag_for_review": True
            }
        }
        
        decision = actions[state].copy()
        decision["state"] = state
        decision["risk_score"] = round(risk, 2)
        decision["student_id"] = agent.student_id
        explanation = agent.get_explanation()
        decision["explanation"] = explanation
        decision["timestamp"] = explanation['timestamp']
        
        return decision
    
    def get_student_message(self, decision: Dict[str, Any]) -> str:
        """
        Generate message to show student
        
        Args:
            decision: Decision dictionary
        
        Returns:
            User-friendly message
        """
        state = decision['state']
        
        messages = {
            "SAFE": "",
            "MILD": "",
            "HIGH": "⚠️ Please ensure you're following exam guidelines. Keep your eyes on the screen and avoid suspicious movements.",
            "CRITICAL": "🚨 Multiple violations detected. A supervisor has been notified. Please remain calm and continue your exam."
        }
        
        return messages.get(state, "")
    
    def get_supervisor_alert(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate supervisor alert
        
        Args:
            decision: Decision dictionary
        
        Returns:
            Alert dictionary for supervisor dashboard
        """
        explanation = decision['explanation']
        
        return {
            "student_id": decision['student_id'],
            "alert_level": decision['state'],
            "risk_score": decision['risk_score'],
            "behavior_state": explanation['behavior_state'],
            "patterns": explanation['patterns_detected'],
            "reasons": explanation['reasons'],
            "violation_count": explanation['violation_count'],
            "session_duration": explanation['session_duration'],
            "timestamp": decision['timestamp'],
            "recommended_action": self._get_recommended_action(decision['state'])
        }
    
    def _get_recommended_action(self, state: DecisionState) -> str:
        """Get recommended action for supervisor"""
        recommendations = {
            "SAFE": "No action needed",
            "MILD": "Monitor student",
            "HIGH": "Review student behavior, consider verbal warning",
            "CRITICAL": "Immediate review required - possible cheating detected"
        }
        return recommendations.get(state, "Monitor student")
