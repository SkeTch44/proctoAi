import os
import json
import logging
import requests
import time
from abc import ABC, abstractmethod
from typing import Dict, Optional, Any
from google import genai

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

class GeminiClient(LLMClient):
    """Client for Google Gemini AI"""
    MIN_CALL_INTERVAL = 4  # seconds between calls for free tier safety
    
    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model_name = model_name
        self._last_call_time = 0
        self.client = genai.Client(api_key=api_key)
        logger.info(f"Initialized GeminiClient with model={model_name} (New SDK)")

    def health_check(self) -> bool:
        return bool(self.api_key)

    def generate_content(self, prompt: str) -> Optional[Any]:
        # Enforce minimum interval between calls
        elapsed = time.time() - self._last_call_time
        if elapsed < self.MIN_CALL_INTERVAL:
            sleep_time = self.MIN_CALL_INTERVAL - elapsed
            logger.info(f"Rate limiting Gemini: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)
            
        try:
            self._last_call_time = time.time()
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={
                    "response_mime_type": "application/json"
                }
            )
            
            # Match current expectations
            class response_wrapper:
                def __init__(self, text):
                    self.text = text
            
            return response_wrapper(response.text)
            
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            if "quota" in str(e).lower() or "429" in str(e):
                 logger.warning("Gemini quota exceeded.")
            return None

class MiniMaxClient(LLMClient):
    """Client for MiniMax API via OpenCode Zen gateway (OpenAI-compatible endpoint)"""

    API_URL = os.getenv("MINIMAX_API_URL", "https://opencode.ai/zen/v1/chat/completions")
    DEFAULT_MODEL = "minimax-m2.5"
    REQUEST_TIMEOUT = 60  # seconds
    HEALTH_CHECK_TIMEOUT = 5  # seconds

    def __init__(self, api_key: str, model: str = None):
        self.api_key = api_key
        self.model = model or os.getenv("MINIMAX_MODEL", self.DEFAULT_MODEL)
        logger.info(f"Initialized MiniMaxClient with model={self.model}")

    def health_check(self) -> bool:
        """Return True if API key is set and a test request succeeds within 5s."""
        if not self.api_key:
            logger.warning("MiniMax health check failed: MINIMAX_API_KEY is empty")
            return False

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": "ping"}],
                "max_completion_tokens": 1
            }
            response = requests.post(
                self.API_URL,
                headers=headers,
                json=payload,
                timeout=self.HEALTH_CHECK_TIMEOUT
            )
            return response.status_code == 200
        except requests.exceptions.Timeout:
            logger.warning("MiniMax health check timed out")
            return False
        except Exception as e:
            logger.warning(f"MiniMax health check failed: {e}")
            return False

    def generate_content(self, prompt: str, **kwargs) -> Optional[Any]:
        """Send prompt to MiniMax chat completions and return response wrapper."""
        if not self.api_key:
            logger.error("MiniMax generate_content failed: MINIMAX_API_KEY is not configured")
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}]
        }

        # Include optional kwargs in request body
        if "temperature" in kwargs and kwargs["temperature"] is not None:
            payload["temperature"] = kwargs["temperature"]
        if "max_completion_tokens" in kwargs and kwargs["max_completion_tokens"] is not None:
            payload["max_completion_tokens"] = kwargs["max_completion_tokens"]

        try:
            response = requests.post(
                self.API_URL,
                headers=headers,
                json=payload,
                timeout=self.REQUEST_TIMEOUT
            )

            if response.status_code != 200:
                logger.error(f"MiniMax API returned HTTP {response.status_code}")
                return None

            data = response.json()

            # Extract content from choices[0].message.content
            try:
                text = data["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError):
                logger.error("MiniMax response missing expected choices[0].message.content structure")
                return None

            class response_wrapper:
                def __init__(self, text):
                    self.text = text

            return response_wrapper(text)

        except requests.exceptions.Timeout:
            logger.warning("MiniMax generate_content request timed out (60s)")
            return None
        except requests.exceptions.HTTPError as e:
            logger.error(f"MiniMax HTTP error: {e}")
            return None
        except Exception as e:
            logger.error(f"MiniMax generation failed: {e}")
            return None


class LLMFactory:
    """Factory to create and manage LLM clients"""
    
    @staticmethod
    def create_client() -> Optional[LLMClient]:
        # Priority 1: MiniMax
        api_key = os.getenv("MINIMAX_API_KEY", "")
        if api_key:
            client = MiniMaxClient(api_key)
            try:
                if client.health_check():
                    logger.info("Using MiniMax as primary LLM")
                    return client
            except Exception as e:
                logger.warning(f"MiniMax health check exception: {e}")

        # Priority 2: Ollama (fallback)
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        ollama_model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
        client = OllamaClient(ollama_url, ollama_model)
        try:
            if client.health_check():
                logger.info("Using Ollama as fallback LLM")
                return client
        except Exception as e:
            logger.warning(f"Ollama health check exception: {e}")

        logger.error("No LLM client available (MiniMax and Ollama both unavailable).")
        return None
