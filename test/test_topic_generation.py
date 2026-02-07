
import unittest
import sys
import os
from unittest.mock import MagicMock

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from questions import QuestionGenerator

class TestTopicGeneration(unittest.TestCase):
    def setUp(self):
        self.qg = QuestionGenerator(rag_store_path="test_rag_store")
        # Mock LLM client to avoid huge API calls and costs during test
        self.qg.llm_client = MagicMock()
        self.qg.llm_client.generate_content.return_value.text = """
        {
            "questions": [
                {
                    "id": "q1",
                    "type": "mcq",
                    "question": "What is Python?",
                    "options": ["A snake", "A language", "A car", "A food"],
                    "correct_answer": "B",
                    "difficulty": "easy",
                    "points": 1
                }
            ]
        }
        """

    def test_topic_only_logic(self):
        """Test that generation proceeds effectively with only a topic"""
        # Call generate_questions with empty content but a valid topic
        questions = self.qg.generate_questions(content="", topic="Python Basics", num_questions=1)
        
        # Verify LLM was called
        self.assertTrue(self.qg.llm_client.generate_content.called)
        
        # Verify arguments passed to prompt creation (indirectly via mock call args if needed, 
        # but here we just check we got a result)
        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0]['question'], "What is Python?")

if __name__ == '__main__':
    unittest.main()
