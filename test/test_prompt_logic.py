import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import json

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.questions import QuestionGenerator

class TestPromptLogic(unittest.TestCase):
    @patch('backend.questions.RAGEngine')
    @patch('backend.questions.LLMFactory')
    def setUp(self, mock_llm_factory, mock_rag_engine):
        self.qg = QuestionGenerator()
        # qg.rag_engine is set in init using the mocked class
        self.qg.rag_engine = mock_rag_engine.return_value
        self.qg.llm_client = mock_llm_factory.create_client.return_value
        self.qg.rag_engine.index.ntotal = 10 

    def test_mcq_prompt_structure(self):
        # Test MCQ Prompt
        prompt = self.qg._get_format_prompt(
            context="Test Context",
            count=5,
            format_type="mcq",
            difficulty="medium",
            topic="History"
        )
        
        self.assertIn("Generate EXACTLY 5 multiple-choice questions.", prompt)
        self.assertIn("ONE sentence", prompt) # Check for "ONE sentence" rule
        self.assertIn("EXACTLY 5", prompt)
        self.assertIn("Context:\nTest Context", prompt)
        self.assertIn('"options": {', prompt) # Check JSON structure hint

    def test_short_answer_prompt_structure(self):
        prompt = self.qg._get_format_prompt(
            context="Test Context",
            count=3,
            format_type="short_answer",
            difficulty="hard",
            topic="Science"
        )
        self.assertIn("Generate EXACTLY 3 questions.", prompt)
        self.assertIn("Expected answer length: 1–3 sentences.", prompt)
        self.assertIn("Context:\nTest Context", prompt)

    def test_descriptive_prompt_structure(self):
        prompt = self.qg._get_format_prompt(
            context="Test Context",
            count=1,
            format_type="descriptive",
            difficulty="expert",
            topic="Philosophy"
        )
        self.assertIn("Generate EXACTLY 1 questions", prompt) # Grammar might be "questions"
        self.assertIn("answer_outline", prompt)

    def test_validator_mcq(self):
        # Simulate LLM output for MCQ
        raw_q = {
            "question": "What is AI?",
            "options": {
                "A": "Artificial Intelligence",
                "B": "Baked Iguana",
                "C": "Cool Ice",
                "D": "Dark Ink"
            },
            "answer": "A"
        }
        
        enhanced = self.qg._validate_and_enhance_question(raw_q, 1, [], "medium", "AI")
        
        self.assertIsNotNone(enhanced)
        self.assertEqual(enhanced['type'], 'mcq')
        self.assertEqual(enhanced['correct_answer'], 'A')
        # Check options conversion: Dict -> List
        self.assertEqual(len(enhanced['options']), 4)
        self.assertEqual(enhanced['options'][0], "A) Artificial Intelligence")
        self.assertEqual(enhanced['options'][1], "B) Baked Iguana")

    def test_validator_short_answer(self):
        raw_q = {
            "question": "Explain things.",
            "expected_answer": "Things are explained."
        }
        
        enhanced = self.qg._validate_and_enhance_question(raw_q, 1, [], "medium", "AI")
        
        self.assertIsNotNone(enhanced)
        self.assertEqual(enhanced['type'], 'short_answer')

        self.assertEqual(enhanced['type'], 'short_answer') 
        self.assertEqual(enhanced['sample_answer'], "Things are explained.")

    def test_validator_essay_outline(self):
        raw_q = {
            "question": "Discuss.",
            "answer_outline": ["Point 1", "Point 2"]
        }
        
        enhanced = self.qg._validate_and_enhance_question(raw_q, 1, [], "expert", "AI")
        
        self.assertIsNotNone(enhanced)
        self.assertEqual(enhanced['type'], 'essay')
        self.assertIn("- Point 1", enhanced['sample_answer'])
        self.assertIn("- Point 2", enhanced['sample_answer'])

if __name__ == '__main__':
    unittest.main()
