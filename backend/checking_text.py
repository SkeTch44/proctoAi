# backend/checking_text.py

import re
import logging
from typing import Dict, Any
from textstat import flesch_reading_ease, flesch_kincaid_grade

logger = logging.getLogger(__name__)

class TextChecker:
    """
    Utility for checking and validating text content.
    Provides:
      - Length checks
      - Readability scores
      - Profanity filtering (basic)
      - Duplicate sentence detection
      - Character entropy analysis
    """

    # Basic profanity list (extend as needed)
    PROFANITY_LIST = {
        "damn", "hell", "shit", "fuck", "bitch", "bastard", "crap"
    }

    def __init__(self):
        pass

    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analyze text and return metrics:
          length, readability, profanity, duplicates, entropy
        """
        result = {
            "length": len(text),
            "word_count": len(text.split()),
            "sentences": [],
            "readability": {},
            "profanity": {},
            "duplicates": [],
            "entropy": 0.0
        }
        try:
            result["sentences"] = self._split_sentences(text)
            result["readability"] = self._compute_readability(text)
            result["profanity"] = self._check_profanity(text)
            result["duplicates"] = self._find_duplicate_sentences(result["sentences"])
            result["entropy"] = self._compute_entropy(text)
        except Exception as e:
            logger.error(f"Text analysis error: {e}")
        return result

    def _split_sentences(self, text: str) -> list:
        # Split on punctuation
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        return [s for s in sentences if s]

    def _compute_readability(self, text: str) -> Dict[str, float]:
        # Using textstat for readability
        try:
            fre = flesch_reading_ease(text)
            fk = flesch_kincaid_grade(text)
            return {
                "flesch_reading_ease": round(fre, 2),
                "flesch_kincaid_grade": round(fk, 2)
            }
        except Exception:
            return {"flesch_reading_ease": None, "flesch_kincaid_grade": None}

    def _check_profanity(self, text: str) -> Dict[str, Any]:
        words = re.findall(r'\w+', text.lower())
        profs = [w for w in words if w in self.PROFANITY_LIST]
        return {
            "contains_profanity": bool(profs),
            "profanity_words": profs
        }

    def _find_duplicate_sentences(self, sentences: list) -> list:
        seen = {}
        duplicates = []
        for s in sentences:
            key = s.strip().lower()
            if key in seen:
                duplicates.append(s)
            else:
                seen[key] = True
        return duplicates

    def _compute_entropy(self, text: str) -> float:
        # Character-level Shannon entropy
        freq = {}
        for ch in text:
            freq[ch] = freq.get(ch, 0) + 1
        entropy = 0.0
        length = len(text)
        for count in freq.values():
            p = count / length
            entropy -= p * (p and __import__('math').log2(p))
        return round(entropy, 4)
