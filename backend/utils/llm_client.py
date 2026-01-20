import os
import json
import logging
import requests
import google.generativeai as genai
from abc import ABC, abstractmethod
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

class LLMClient(ABC):
    """Abstract base class for LLM clients"""
    
    @abstractmethod
    def generate_content(self, prompt: str) -> Optional[Any]:
        """Generate content from the LLM"""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """Check if the LLM service is available"""
        pass

class OllamaClient(LLMClient):
    """Client for local Ollama instance"""
    
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.api_url = f"{self.base_url}/api/generate"
        logger.info(f"Initialized OllamaClient with model={model} at {base_url}")

    def health_check(self) -> bool:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False

    def generate_content(self, prompt: str) -> Optional[Any]:
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.3,
                    "num_ctx": 4096 
                }
            }
            
            response = requests.post(self.api_url, json=payload, timeout=60)
            response.raise_for_status()
            
            data = response.json()
            response_text = data.get("response", "")
            
            # Simple wrapper object to match Gemini's interface slightly or just return text
            # The calling code expects an object with .text attribute usually if it was designed for Gemini,
            # but we can return a simple object or just the text and handle it in the caller.
            # To minimize changes in questions.py, let's look at how it consumes it.
            # questions.py consumes `response.text`.
            
            class response_wrapper:
                def __init__(self, text):
                    self.text = text
            
            return response_wrapper(response_text)
            
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            return None

class GeminiClient(LLMClient):
    """Wrapper for Google Gemini API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel("gemini-2.0-flash")
            self.available = True
        except Exception as e:
            logger.error(f"Gemini init failed: {e}")
            self.available = False

    def health_check(self) -> bool:
        return self.available and bool(self.api_key)

    def generate_content(self, prompt: str) -> Optional[Any]:
        if not self.available:
            return None
        try:
            return self.model.generate_content(prompt)
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            return None

class LLMFactory:
    """Factory to create and manage LLM clients with fallback strategy"""
    
    @staticmethod
    def create_client() -> LLMClient:
        # Priority 1: Ollama
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        ollama_model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
        
        ollama_client = OllamaClient(ollama_url, ollama_model)
        if ollama_client.health_check():
            logger.info("Using Ollama as primary LLM")
            return ollama_client
        
        logger.warning("Ollama not available, falling back to Gemini")
        
        # Priority 2: Gemini
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            gemini_client = GeminiClient(gemini_key)
            if gemini_client.health_check():
                logger.info("Using Gemini as fallback LLM")
                return gemini_client
        
        logger.error("No LLM available (Ollama down, Gemini not configured)")
        return None
