import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.utils.llm_client import LLMFactory, OllamaClient, GeminiClient

class TestLLMFallback(unittest.TestCase):
    
    @patch.dict(os.environ, {"OLLAMA_BASE_URL": "http://bad-url:123456", "GEMINI_API_KEY": "fake-key"})
    @patch('backend.utils.llm_client.requests.get')
    def test_fallback_to_gemini(self, mock_get):
        """Test fallback to Gemini when Ollama is down"""
        print("\nTesting Fallback Logic: Ollama Down -> Gemini Up")
        
        # Mock Ollama health check failure
        mock_get.side_effect = Exception("Connection refused")
        
        # Mock Gemini available (GeminiClient init checks config, we mock it)
        with patch('google.generativeai.configure'), \
             patch('google.generativeai.GenerativeModel') as MockGemini:
            
            client = LLMFactory.create_client()
            
            self.assertIsInstance(client, GeminiClient, "Should return GeminiClient when Ollama is down")
            print("✓ Fallback to Gemini successful")

    @patch.dict(os.environ, {"OLLAMA_BASE_URL": "http://localhost:11434"})
    @patch('backend.utils.llm_client.requests.get')
    def test_ollama_primary(self, mock_get):
        """Test Ollama is primary when available"""
        print("\nTesting Primary Logic: Ollama Up")
        
        # Mock Ollama health check success
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        mock_get.side_effect = None
        
        client = LLMFactory.create_client()
        
        self.assertIsInstance(client, OllamaClient, "Should return OllamaClient when available")
        print("✓ Primary Ollama selection successful")

if __name__ == '__main__':
    unittest.main()
