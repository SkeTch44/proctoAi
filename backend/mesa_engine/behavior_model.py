"""
Mesa Behavior Model - Manages all student agents
"""

from mesa import Model
from mesa.time import RandomActivation
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
        self.schedule = RandomActivation(self)
        self.agents_by_student: Dict[str, StudentAgent] = {}
        self.current_id = 0
        
        logger.info("BehaviorModel initialized")
    
    def add_student(self, student_id: str) -> StudentAgent:
        """
        Add a new student agent
        
        Args:
            student_id: Student identifier
        
        Returns:
            Created StudentAgent
        """
        agent = StudentAgent(self.current_id, self, student_id)
        self.schedule.add(agent)
        self.agents_by_student[student_id] = agent
        self.current_id += 1
        
        logger.info(f"Added student agent: {student_id}")
        return agent
    
    def get_student_agent(self, student_id: str) -> StudentAgent:
        """
        Get agent for a student (creates if doesn't exist)
        
        Args:
            student_id: Student identifier
        
        Returns:
            StudentAgent instance
        """
        if student_id not in self.agents_by_student:
            return self.add_student(student_id)
        return self.agents_by_student[student_id]
    
    def remove_student(self, student_id: str):
        """
        Remove a student agent (e.g., when exam ends)
        
        Args:
            student_id: Student identifier
        """
        if student_id in self.agents_by_student:
            agent = self.agents_by_student[student_id]
            self.schedule.remove(agent)
            del self.agents_by_student[student_id]
            logger.info(f"Removed student agent: {student_id}")
    
    def get_all_explanations(self) -> Dict[str, Dict]:
        """
        Get explanations for all students
        
        Returns:
            Dictionary mapping student_id to explanation
        """
        return {
            student_id: agent.get_explanation()
            for student_id, agent in self.agents_by_student.items()
        }
    
    def get_flagged_students(self) -> list:
        """
        Get list of students in FLAGGED state
        
        Returns:
            List of student IDs
        """
        return [
            student_id
            for student_id, agent in self.agents_by_student.items()
            if agent.behavior_state == "FLAGGED"
        ]
    
    def step(self):
        """
        Run one step of the model
        Called every second by Mesa service
        """
        self.schedule.step()
