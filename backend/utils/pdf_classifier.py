
import json
import logging
import requests
from typing import Dict, Any
from backend.config import Config

logger = logging.getLogger(__name__)

class PDFChunkClassifier:
    """
    LLM-based chunk classification (NOT generation).
    Uses small, fast models to label text chunks.
    """
    
    CLASSIFICATION_PROMPT = """
You are a strict data classifier. Classify the following text into ONE category:
- QUESTION: A question being asked
- OPTION: Multiple choice options (A, B, C, D)
- ANSWER: The correct answer or solution
- EXPLANATION: Detailed explanation of the answer
- NOISE: Irrelevant content (headers, footers, page numbers)

Text to classify:
"{text}"

Return ONLY a JSON object with this exact format:
{{
    "type": "CATEGORY",
    "confidence": 0.0 to 1.0
}}
Do not add any other text.
"""

    def __init__(self, model: str = None):
        self.model = model or Config.OLLAMA_MODEL
        self.api_url = f"{Config.OLLAMA_BASE_URL}/api/generate"

    def classify(self, text: str) -> Dict[str, Any]:
        """
        Classify a text chunk.
        
        Returns:
            {
                "type": "QUESTION" | "OPTION" | "ANSWER" | "EXPLANATION" | "NOISE",
                "confidence": float
            }
        """
        prompt = self.CLASSIFICATION_PROMPT.format(text=text[:1000]) # Trucate to avoid context limits
        
        try:
            response = requests.post(self.api_url, json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": "json", # Force JSON mode
                "options": {
                    "temperature": 0.0, # Deterministic
                    "num_predict": 128
                }
            }, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                content = result.get('response', '{}')
                return self._parse_response(content)
            else:
                logger.error(f"Classification failed: {response.status_code}")
                return {"type": "NOISE", "confidence": 0.0}
                
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return {"type": "NOISE", "confidence": 0.0}

    def _parse_response(self, content: str) -> Dict[str, Any]:
        """Parse LLM JSON output with fallback"""
        try:
            data = json.loads(content)
            
            # Normalize
            if 'type' in data:
                data['type'] = data['type'].upper()
                if data['type'] not in ['QUESTION', 'OPTION', 'ANSWER', 'EXPLANATION', 'NOISE']:
                    data['type'] = 'NOISE'
                    
            if 'confidence' not in data:
                data['confidence'] = 0.5
                
            return data
            
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON from LLM: {content}")
            # Simple fallback heuristic if JSON fails
            lower = content.lower()
            if "question" in lower: return {"type": "QUESTION", "confidence": 0.5}
            if "answer" in lower: return {"type": "ANSWER", "confidence": 0.5}
            return {"type": "NOISE", "confidence": 0.0}
