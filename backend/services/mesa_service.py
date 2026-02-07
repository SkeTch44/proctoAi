"""
Mesa Service - Background service running Mesa ABM engine
Coordinates event consumption, agent updates, decision making, and storage
"""

from backend.mesa_engine.behavior_model import BehaviorModel
from backend.risk_engine.decision_maker import DecisionMaker
from backend.storage.timeline_store import TimelineStore
from backend.events.publisher import EventConsumer
import threading
import time
import logging
from typing import Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)


class MesaService:
    """
    Background service running Mesa ABM engine
    
    Responsibilities:
    - Consume events from Redis Stream
    - Feed events to StudentAgents
    - Run Mesa model step (every 1 second)
    - Make decisions based on risk
    - Store timeline for explainability
    - Trigger alerts/notifications
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        stream_name: str = "proctoring_events",
        step_interval: float = 1.0,
        alert_callback: Optional[Callable] = None
    ):
        """
        Initialize Mesa service
        
        Args:
            redis_url: Redis connection URL
            stream_name: Redis stream name
            step_interval: Seconds between model steps
            alert_callback: Function to call when alerts triggered
        """
        self.step_interval = step_interval
        self.alert_callback = alert_callback
        
        # Initialize components
        self.model = BehaviorModel()
        self.decision_maker = DecisionMaker()
        self.timeline_store = TimelineStore()
        
        # Event consumer
        self.redis_url = redis_url
        self.stream_name = stream_name
        
        # Event consumer (lazy init in background thread)
        self.event_consumer = None
        self.events_enabled = False
        
        # Service state
        self.running = False
        self.thread = None
        
        # Statistics
        self.total_events_processed = 0
        self.total_decisions_made = 0
        self.total_alerts_sent = 0
        
        logger.info("MesaService initialized")
    
    def start(self):
        """Start the Mesa service"""
        if self.running:
            logger.warning("MesaService already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info("MesaService started")
    
    def stop(self):
        """Stop the Mesa service"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("MesaService stopped")
    
    def _run_loop(self):
        """
        Main loop - runs every step_interval seconds
        """
        logger.info("MesaService loop started")
        
        # Initialize EventConsumer here to avoid blocking main thread on import
        if not self.event_consumer:
            try:
                self.event_consumer = EventConsumer(self.redis_url, self.stream_name)
                self.events_enabled = self.event_consumer.enabled
            except Exception as e:
                logger.warning(f"Event consumer failed to initialize in background: {e}")
                self.events_enabled = False
        
        while self.running:
            try:
                # 1. Consume events from Redis
                if self.events_enabled:
                    events = self.event_consumer.read_events(count=100, block=0)
                    for event in events:
                        self._process_event(event)
                
                # 2. Step the Mesa model
                self.model.step()
                
                # 3. Make decisions for all agents
                for student_id, agent in self.model.agents_by_student.items():
                    decision = self.decision_maker.make_decision(agent)
                    self._handle_decision(student_id, decision)
                
                # Sleep until next step
                time.sleep(self.step_interval)
                
            except Exception as e:
                logger.error(f"Error in Mesa service loop: {e}", exc_info=True)
                time.sleep(self.step_interval)
    
    def _process_event(self, event: Dict[str, Any]):
        """
        Process a single event
        
        Args:
            event: Event dictionary from Redis
        """
        try:
            student_id = event.get('student_id')
            if not student_id:
                logger.warning("Event missing student_id")
                return
            
            # Get or create agent
            agent = self.model.get_student_agent(student_id)
            
            # Feed event to agent
            agent.observe(event)
            
            self.total_events_processed += 1
            
        except Exception as e:
            logger.error(f"Failed to process event: {e}")
    
    def _handle_decision(self, student_id: str, decision: Dict[str, Any]):
        """
        Handle decision output
        
        Args:
            student_id: Student identifier
            decision: Decision dictionary
        """
        try:
            # Store timeline entry
            self.timeline_store.add_entry(student_id, decision['explanation'])
            
            self.total_decisions_made += 1
            
            # Handle alerts
            if decision.get('notify_supervisor'):
                self._send_supervisor_alert(decision)
            
            if decision.get('notify_student'):
                self._send_student_notification(decision)
            
            # Log critical decisions
            if decision['state'] == 'CRITICAL':
                logger.warning(
                    f"CRITICAL decision for {student_id}: "
                    f"Risk={decision['risk_score']}, "
                    f"Patterns={decision['explanation']['patterns_detected']}"
                )
            
        except Exception as e:
            logger.error(f"Failed to handle decision: {e}")
    
    def _send_supervisor_alert(self, decision: Dict[str, Any]):
        """Send alert to supervisor"""
        try:
            alert = self.decision_maker.get_supervisor_alert(decision)
            
            if self.alert_callback:
                self.alert_callback('supervisor', alert)
            
            self.total_alerts_sent += 1
            logger.info(f"Supervisor alert sent for {decision['student_id']}")
            
        except Exception as e:
            logger.error(f"Failed to send supervisor alert: {e}")
    
    def _send_student_notification(self, decision: Dict[str, Any]):
        """Send notification to student"""
        try:
            message = self.decision_maker.get_student_message(decision)
            
            if message and self.alert_callback:
                self.alert_callback('student', {
                    'student_id': decision['student_id'],
                    'message': message,
                    'level': decision['state']
                })
            
            logger.info(f"Student notification sent for {decision['student_id']}")
            
        except Exception as e:
            logger.error(f"Failed to send student notification: {e}")
    
    def get_student_status(self, student_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current status for a student
        
        Args:
            student_id: Student identifier
        
        Returns:
            Status dictionary or None
        """
        if student_id in self.model.agents_by_student:
            agent = self.model.agents_by_student[student_id]
            decision = self.decision_maker.make_decision(agent)
            return decision
        return None
    
    def get_all_statuses(self) -> Dict[str, Dict[str, Any]]:
        """
        Get statuses for all students
        
        Returns:
            Dictionary mapping student_id to status
        """
        return {
            student_id: self.decision_maker.make_decision(agent)
            for student_id, agent in self.model.agents_by_student.items()
        }
    
    def get_flagged_students(self) -> list:
        """
        Get list of flagged students
        
        Returns:
            List of student IDs in FLAGGED state
        """
        return self.model.get_flagged_students()
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get service statistics
        
        Returns:
            Statistics dictionary
        """
        return {
            "running": self.running,
            "total_students": len(self.model.agents_by_student),
            "total_events_processed": self.total_events_processed,
            "total_decisions_made": self.total_decisions_made,
            "total_alerts_sent": self.total_alerts_sent,
            "flagged_students": len(self.get_flagged_students())
        }
    
    def remove_student(self, student_id: str):
        """
        Remove a student (e.g., when exam ends)
        
        Args:
            student_id: Student identifier
        """
        self.model.remove_student(student_id)
        self.timeline_store.clear_student(student_id)
        logger.info(f"Removed student: {student_id}")
