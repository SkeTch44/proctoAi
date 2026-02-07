import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from backend.utils.llm_client import LLMFactory, OllamaClient, GeminiClient

class TestLLMPriority(unittest.TestCase):

    def setUp(self):
        # Reset env vars for clean test
        self.env_patcher = patch.dict(os.environ, {
            "GEMINI_API_KEY": "fake_gemini_key",
            "OLLAMA_BASE_URL": "http://localhost:11434"
        })
        self.env_patcher.start()

    def tearDown(self):
        self.env_patcher.stop()

    @patch('backend.utils.llm_client.OllamaClient.health_check')
    @patch('backend.utils.llm_client.GeminiClient.health_check')
    def test_llama_priority_when_both_available(self, mock_gemini_health, mock_ollama_health):
        # Scenario 1: Both UP
        mock_ollama_health.return_value = True
        mock_gemini_health.return_value = True
        
        client = LLMFactory.create_client()
        
        print(f"Scenario 1 (Both UP) -> Client: {client.__class__.__name__}")
        self.assertIsInstance(client, OllamaClient, "Should return OllamaClient when Ollama is UP")

    @patch('backend.utils.llm_client.OllamaClient.health_check')
    @patch('backend.utils.llm_client.GeminiClient.health_check')
    def test_gemini_fallback_when_ollama_down(self, mock_gemini_health, mock_ollama_health):
        # Scenario 2: Ollama DOWN, Gemini UP
        mock_ollama_health.return_value = False
        mock_gemini_health.return_value = True
        
        client = LLMFactory.create_client()
        
        print(f"Scenario 2 (Ollama DOWN, Gemini UP) -> Client: {client.__class__.__name__}")
        self.assertIsInstance(client, GeminiClient, "Should fall back to GeminiClient when Ollama is DOWN")

    @patch('backend.utils.llm_client.OllamaClient.health_check')
    @patch('backend.utils.llm_client.GeminiClient.health_check')
    def test_none_when_both_down(self, mock_gemini_health, mock_ollama_health):
        # Scenario 3: Both DOWN
        mock_ollama_health.return_value = False
        mock_gemini_health.return_value = False
        
        client = LLMFactory.create_client()
        
        print(f"Scenario 3 (Both DOWN) -> Client: {client}")
        self.assertIsNone(client, "Should return None when both services are DOWN")

if __name__ == '__main__':
    unittest.main()
