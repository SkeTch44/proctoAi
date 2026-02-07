import os
import json
import logging
import requests
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
            
            # Simple wrapper object to match potential interface expectations
            class response_wrapper:
                def __init__(self, text):
                    self.text = text
            
            return response_wrapper(response_text)
            
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            return None

class LLMFactory:
    """Factory to create and manage LLM clients"""
    
    @staticmethod
    def create_client() -> Optional[LLMClient]:
        # Priority: Ollama ONLY
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        ollama_model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
        
        ollama_client = OllamaClient(ollama_url, ollama_model)
        if ollama_client.health_check():
            logger.info("Using Ollama as primary LLM")
            return ollama_client
        
        logger.error("Ollama not available. No LLM client created.")
        return None
