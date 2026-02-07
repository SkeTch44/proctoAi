import unittest
from unittest.mock import patch, MagicMock
from backend.qa_agent import AntigravityQA, ANTIGRAVITY_QA_SYSTEM_PROMPT

class TestAntigravityQA(unittest.TestCase):
    
    @patch('backend.qa_agent.LLMRunner')
    def test_run_qa_check_success(self, mock_llm_runner):
        # Setup
        mock_input = {
            "exam_id": "exam_123",
            "questions": [{"id": 1, "text": "Q1"}],
            "stage": "pre_publish"
        }
        
        expected_verdict = {
            "verdict": "PASS",
            "confidence": 0.99,
            "blocking": False,
            "reasons": [],
            "recommendation": "Publish allowed"
        }
        
        mock_llm_runner.run_batch.return_value = expected_verdict
        
        # Execute
        result = AntigravityQA.run_qa_check(mock_input)
        
        # Assert
        self.assertEqual(result, expected_verdict)
        mock_llm_runner.run_batch.assert_called_once()
        
        # Check args passed to LLMRunner
        args, _ = mock_llm_runner.run_batch.call_args
        blueprint, batch_config, skill_metadata = args
        
        self.assertEqual(blueprint['system'], ANTIGRAVITY_QA_SYSTEM_PROMPT)
        self.assertIn('"exam_id": "exam_123"', blueprint['user'])
        self.assertEqual(batch_config['type'], 'validation')
        self.assertEqual(skill_metadata['skill_id'], 'antigravity_qa')
        self.assertEqual(skill_metadata['llm_params']['temperature'], 0.1)

    @patch('backend.qa_agent.LLMRunner')
    def test_run_qa_check_failure(self, mock_llm_runner):
        # Simulate LLM failure (None return)
        mock_llm_runner.run_batch.return_value = None
        
        result = AntigravityQA.run_qa_check({"test": "data"})
        
        self.assertEqual(result['verdict'], "FAIL")
        self.assertTrue(result['blocking'])
        self.assertEqual(result['reasons'][0]['type'], "SYSTEM_ERROR")

if __name__ == '__main__':
    unittest.main()
