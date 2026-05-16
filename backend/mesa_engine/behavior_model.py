"""
Mesa Behavior Model - Manages all student agents
Compatible with Mesa 3.x (no RandomActivation — agents managed directly)
"""

try:
    from mesa import Model
    from mesa.time import RandomActivation
    MESA_V2 = True
except ImportError:
    try:
        from mesa import Model
        MESA_V2 = False  # Mesa 3.x
    except ImportError:
        Model = object
        MESA_V2 = False

from .student_agent import StudentAgent
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class BehaviorModel(Model):
    """
    Mesa Model managing all student agents
    Coordinates behavioral analysis across all students
    """
    
    def __init__(self):
        """Initialize the behavior model"""
        super().__init__()
        if MESA_V2:
            self.schedule = RandomActivation(self)
        self.agents_by_student: Dict[str, StudentAgent] = {}
        self.current_id = 0
        
        logger.info("BehaviorModel initialized")
    
    def add_student(self, student_id: str) -> StudentAgent:
        agent = StudentAgent(self.current_id, self, student_id)
        if MESA_V2:
            self.schedule.add(agent)
        self.agents_by_student[student_id] = agent
        self.current_id += 1
        logger.info(f"Added student agent: {student_id}")
        return agent
    
    def get_student_agent(self, student_id: str) -> StudentAgent:
        if student_id not in self.agents_by_student:
            return self.add_student(student_id)
        return self.agents_by_student[student_id]
    
    def remove_student(self, student_id: str):
        if student_id in self.agents_by_student:
            agent = self.agents_by_student[student_id]
            if MESA_V2:
                self.schedule.remove(agent)
            del self.agents_by_student[student_id]
            logger.info(f"Removed student agent: {student_id}")
    
    def get_all_explanations(self) -> Dict[str, Dict]:
        return {
            student_id: agent.get_explanation()
            for student_id, agent in self.agents_by_student.items()
        }
    
    def get_flagged_students(self) -> list:
        return [
            student_id
            for student_id, agent in self.agents_by_student.items()
            if agent.behavior_state == "FLAGGED"
        ]
    
    def step(self):
        """Run one step of the model"""
        if MESA_V2:
            self.schedule.step()
        else:
            # Mesa 3.x: step agents directly
            for agent in self.agents_by_student.values():
                agent.step()
