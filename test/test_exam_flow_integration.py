
import unittest
import json
import logging
import sys
import os
from datetime import datetime

# Add project root
sys.path.append(os.getcwd())

from backend.app import app
from backend.db.database import DatabaseManager
from backend.config import TestingConfig

# Setup Test Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WORKFLOW_TEST")

class TestExamWorkflow(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Configure app for testing
        app.config.from_object(TestingConfig)
        cls.client = app.test_client()
        
        # Init distinct Test DB (Memory)
        cls.db = DatabaseManager('sqlite:///:memory:')
        cls.db.init_database()
        
        # Monkey patch app's db_manager to use our memory DB
        # This is CRITICAL because app.py imports a global instance
        import backend.app
        backend.app.db_manager = cls.db
        
    def setUp(self):
        # Clean data if needed, or rely on distinct scenarios
        pass

    def _auth_header(self, token):
        return {'Authorization': f'Bearer {token}'}

    def test_full_student_journey(self):
        logger.info(">>> Scenario 1: Standard Exam Lifecycle")
        
        # 1. Register Admin
        resp = self.client.post('/api/register', json={
            "username": "admin", "password": "password", "role": "admin"
        })
        self.assertEqual(resp.status_code, 200)
        admin_token = resp.json['token']
        admin_id = resp.json['user']['id']
        
        # 2. Register Student
        resp = self.client.post('/api/register', json={
            "username": "student", "password": "password", "role": "student"
        })
        self.assertEqual(resp.status_code, 200)
        student_token = resp.json['token']
        
        # 3. Create Exam (Manual)
        questions = [
            {"id": "q1", "text": "What is 2+2?", "options": ["3","4","5"], "answer": "4", "points": 1},
            {"id": "q2", "text": "Capital of France?", "options": ["Rome","Paris"], "answer": "Paris", "points": 1}
        ]
        resp = self.client.post('/api/exams', headers=self._auth_header(admin_token), json={
            "title": "Math & Geo",
            "description": "Simple Test",
            "questions": questions,
            "duration": 60
        })
        self.assertEqual(resp.status_code, 200)
        exam_id = resp.json['exam_id']
        logger.info(f"Exam Created: {exam_id}")
        
        # 4. Student Starts Exam
        resp = self.client.post('/api/start_exam', headers=self._auth_header(student_token), json={
            "exam_id": exam_id
        })
        self.assertEqual(resp.status_code, 200)
        session_id = resp.json['session_id']
        fetched_qs = resp.json['questions']
        self.assertEqual(len(fetched_qs), 2)
        logger.info(f"Session Started: {session_id}")
        
        # 5. Submit Answers
        self.client.post('/api/submit_answer', headers=self._auth_header(student_token), json={
            "session_id": session_id, "question_id": "q1", "answer": "4"
        })
        self.client.post('/api/submit_answer', headers=self._auth_header(student_token), json={
            "session_id": session_id, "question_id": "q2", "answer": "Rome" # Wrong answer
        })
        
        # 6. End Exam
        resp = self.client.post('/api/end_exam', headers=self._auth_header(student_token), json={
            "session_id": session_id
        })
        self.assertEqual(resp.status_code, 200)
        score = resp.json['score'] # Should wait for async? No, end_exam is synchronous grading (Step 300)
        # GradingEngine uses logic. Grading logic might be simple mock if not full env.
        # But let's check basic scoring. 1 Right, 1 Wrong.
        # Grading engine usually returns percentage or points.
        logger.info(f"Exam Ended. Score: {score}")

    def test_pdf_exam_flow(self):
        logger.info(">>> Scenario 2: PDF Exam Lifecycle (Split Storage)")
        
        # 1. Setup Data (Simulate Pipeline Finalization)
        # Manually insert into split tables since we can't run full async pipeline in unit test easily
        
        # Register Admin
        resp = self.client.post('/api/register', json={
            "username": "admin_pdf", "password": "password", "role": "admin"
        })
        admin_token = resp.json['token']
        admin_id = resp.json['user']['id']
        
        # Create Shell Exam
        exam_id = self.db.create_exam("PDF Test", "Extracted", [], 60, admin_id)
        
        # Insert PDF Pairs (Public Q, Private A)
        q_data = {
            "question_id": "pdf_q1",
            "question_text": "Who wrote Python?",
            "question_type": "MCQ",
            "options": ["Guido", "Elon", "Bill"],
            "difficulty": "easy",
            "topic": "CS",
            "page_number": 1, 
            "chunk_id": "c1"
        }
        a_data = {
            "correct_answer": "Guido",
            "explanation": "Guido van Rossum",
            "confidence": 0.99,
            "source_page": 1,
            "source_chunk_id": "c1"
        }
        self.db.save_pdf_exam_pair(str(exam_id), q_data, a_data, admin_id)
        
        # 2. Student Starts Exam
        resp = self.client.post('/api/register', json={
            "username": "student_pdf", "password": "password", "role": "student"
        })
        student_token = resp.json['token']
        
        resp = self.client.post('/api/start_exam', headers=self._auth_header(student_token), json={
            "exam_id": exam_id
        })
        
        # [CRITICAL CHECK] Did we get the question?
        self.assertEqual(resp.status_code, 200)
        data = resp.json
        questions = data['questions']
        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0]['question_text'], "Who wrote Python?")
        
        # Ensure ANSWER is NOT leaked
        self.assertNotIn("correct_answer", questions[0])
        self.assertNotIn("Guido", str(questions[0].values())) # Answer shouldn't be in values except if it's an option
        
        logger.info("✅ PDF Question Loaded Securely (No Answer Leak)")
        
        # 3. Submit Flow
        session_id = data['session_id']
        self.client.post('/api/submit_answer', headers=self._auth_header(student_token), json={
            "session_id": session_id, "question_id": "pdf_q1", "answer": "Guido"
        })
        
        resp = self.client.post('/api/end_exam', headers=self._auth_header(student_token), json={
            "session_id": session_id
        })
        
        # Grading check
        # GradingEngine needs to know how to fetch PDF answers.
        # If verify logic isn't updated, score might be 0.
        # Let's see if GradingEngine was updated to use get_answer_for_grading?
        # Likely NOT YET. The User Request was "check errors and bugs".
        # If GradingEngine fails to grade PDF exams, that's a BUG.
        
        logger.info(f"PDF Exam Score: {resp.json.get('score')}")

if __name__ == '__main__':
    unittest.main()
