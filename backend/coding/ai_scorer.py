"""
AI-driven code review/scoring for coding submissions.

Calls the configured LLM (MiniMax with Ollama fallback) and returns a
structured rubric with 100-point total score split across:

  - correctness (0-40)
  - code_quality (0-25)
  - complexity_analysis (0-20)
  - style_readability (0-15)

Falls back to a deterministic test-pass-rate score if the LLM is unavailable
or returns malformed output. Designed to never raise to the caller.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


SCORING_PROMPT = """You are an expert DSA code reviewer. Evaluate the student's code below.

PROBLEM:
{problem_description}

STUDENT CODE ({language}):
```
{source_code}
```

TEST RESULTS: {tests_passed}/{tests_total} passed
EXECUTION: {execution_time_ms}ms

Return ONLY a JSON object with this exact shape:
{{
  "total_score": <int 0-100, sum of section scores>,
  "correctness": {{"score": <0-40>, "feedback": "<one sentence>"}},
  "code_quality": {{"score": <0-25>, "feedback": "<one sentence>"}},
  "complexity_analysis": {{
    "score": <0-20>,
    "time_complexity": "<O(...)>",
    "space_complexity": "<O(...)>",
    "feedback": "<one sentence>"
  }},
  "style_readability": {{"score": <0-15>, "feedback": "<one sentence>"}},
  "overall_feedback": "<2-3 sentences summarizing strengths/weaknesses>",
  "suggestions": ["<actionable improvement 1>", "<actionable improvement 2>"]
}}

Rules: respond with valid JSON only. No prose before or after.
"""


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    """LLMs sometimes wrap JSON in ```json fences or add prose. Pull the JSON out."""
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass

    # Strip code fences
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except Exception:
            pass

    # Greedy: first { ... last }
    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last != -1 and last > first:
        candidate = text[first : last + 1]
        try:
            return json.loads(candidate)
        except Exception:
            return None
    return None


def _fallback_score(tests_passed: int, tests_total: int) -> Dict[str, Any]:
    correctness = int((tests_passed / max(tests_total, 1)) * 40)
    return {
        "total_score": correctness + 15,
        "correctness": {
            "score": correctness,
            "feedback": f"Passed {tests_passed}/{tests_total} test cases.",
        },
        "code_quality": {"score": 10, "feedback": "AI review unavailable."},
        "complexity_analysis": {
            "score": 5,
            "time_complexity": "Unknown",
            "space_complexity": "Unknown",
            "feedback": "AI review unavailable.",
        },
        "style_readability": {"score": 5, "feedback": "AI review unavailable."},
        "overall_feedback": "Automated scoring based on test results only. AI review unavailable.",
        "suggestions": [],
        "ai_available": False,
    }


def _normalize(rubric: Dict[str, Any], tests_passed: int, tests_total: int) -> Dict[str, Any]:
    """Make sure the rubric has the expected shape and reasonable totals."""
    expected = {
        "correctness": (0, 40),
        "code_quality": (0, 25),
        "complexity_analysis": (0, 20),
        "style_readability": (0, 15),
    }

    total = 0
    for key, (lo, hi) in expected.items():
        section = rubric.get(key)
        if not isinstance(section, dict):
            section = {"score": 0, "feedback": ""}
            rubric[key] = section
        try:
            score = int(section.get("score", 0))
        except (TypeError, ValueError):
            score = 0
        score = max(lo, min(hi, score))
        section["score"] = score
        total += score

    rubric.setdefault("overall_feedback", "")
    rubric.setdefault("suggestions", [])
    if not isinstance(rubric.get("suggestions"), list):
        rubric["suggestions"] = []

    # Recompute total to be safe
    rubric["total_score"] = total
    rubric.setdefault("ai_available", True)
    return rubric


def score_code(
    problem_description: str,
    source_code: str,
    language: str,
    tests_passed: int,
    tests_total: int,
    execution_time_ms: int = 0,
) -> Dict[str, Any]:
    """Synchronous AI rubric scoring. Always returns a rubric dict."""
    try:
        from backend.providers.llm_provider import get_llm_client
    except Exception as e:  # noqa: BLE001
        logger.warning(f"LLM provider unavailable: {e}")
        return _fallback_score(tests_passed, tests_total)

    prompt = SCORING_PROMPT.format(
        problem_description=(problem_description or "")[:2000],
        language=language,
        source_code=(source_code or "")[:4000],
        tests_passed=tests_passed,
        tests_total=tests_total,
        execution_time_ms=execution_time_ms,
    )

    try:
        client = get_llm_client()
        resp = client.generate_content(prompt, temperature=0.2, max_completion_tokens=1024)
        if resp is None or not getattr(resp, "text", None):
            logger.warning("LLM returned empty response for code scoring")
            return _fallback_score(tests_passed, tests_total)

        rubric = _extract_json(resp.text)
        if not rubric:
            logger.warning("Could not parse JSON rubric from LLM response")
            return _fallback_score(tests_passed, tests_total)

        return _normalize(rubric, tests_passed, tests_total)

    except Exception as e:  # noqa: BLE001
        logger.exception(f"AI scoring failed: {e}")
        return _fallback_score(tests_passed, tests_total)
