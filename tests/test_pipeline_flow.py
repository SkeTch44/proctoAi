import unittest
from unittest.mock import MagicMock, patch
import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.engine.planner import Planner
from backend.engine.blueprints import BlueprintGenerator
from backend.validator import Validator
# We mock LLMRunner to avoid actual calls

class TestPipeline(unittest.TestCase):
    
    def test_planner_structure(self):
        """Phase 1: Verify Planner creates strict blueprint"""
        request = {
            "topic": "Python", 
            "difficulty": "medium",
            "format": {"mcq": 12, "essay": 2}
        }
        user_id = "test_user"
        
        blueprint = Planner.create_blueprint(request, user_id)
        
        # Check Batches
        # MCQ: 12 -> 5, 5, 2 (3 batches)
        # Essay: 2 -> 1, 1 (2 batches)
        # Total batches: 5
        self.assertEqual(len(blueprint.batches), 5)
        
        mcq_batches = [b for b in blueprint.batches if b['type'] == 'mcq']
        self.assertEqual(len(mcq_batches), 3)
        self.assertEqual(mcq_batches[0]['count'], 5)
        self.assertEqual(mcq_batches[1]['count'], 5)
        self.assertEqual(mcq_batches[2]['count'], 2)
        
        essay_batches = [b for b in blueprint.batches if b['type'] == 'essay']
        self.assertEqual(len(essay_batches), 2)
        self.assertEqual(essay_batches[0]['count'], 1)
        
        print("Planner Test Passed")

    def test_blueprint_generator(self):
        """Phase 2: Verify Blueprint prompt generation"""
        batch = {
            "type": "mcq",
            "count": 5,
            "topic": "History",
            "difficulty": "hard",
            "batch_id": "b1"
        }
        
        prompt_pkg = BlueprintGenerator.get_template(batch)
        self.assertIn("Generate 5 Multiple Choice Questions", prompt_pkg['user'])
        self.assertIn("OUTPUT SCHEMA (JSON Array)", prompt_pkg['user'])
        print("Blueprint Test Passed")

    def test_validator(self):
        """Phase 5: Verify Validator logic"""
        # Good MCQ
        good_data = [
            {
                "question": "Q1",
                "options": ["A", "B", "C", "D"], # validator accepts list or dict
                "answer": "A"
            }
        ]
        # Bad MCQ (only 3 options)
        bad_data = [
            {
                "question": "Q2",
                "options": ["A", "B", "C"],
                "answer": "A"
            }
        ]
        
        valid = Validator.validate_batch(good_data, 'mcq', 1)
        self.assertEqual(len(valid), 1)
        
        invalid = Validator.validate_batch(bad_data, 'mcq', 1)
        self.assertEqual(len(invalid), 0)
        
        print("Validator Test Passed")

if __name__ == '__main__':
    unittest.main()
