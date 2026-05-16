"""
AI Code Scorer — evaluates code quality beyond pass/fail test cases.

Scoring dimensions:
  1. Correctness (from Judge0 test results) — 40%
  2. Code Quality (AI review) — 25%
  3. Time/Space Complexity (AI analysis) — 20%
  4. Code Style & Readability — 15%

The AI scorer calls Ollama (local LLM) to analyze the code and produce
a structured rubric score. Results go to the admin dashboard for review.
"""

import json
import logging
from typing import Dict, Optional

import httpx

from app.core.config import get_settings

logger = logging.getLogger("coding-svc.ai_scorer")

# Scoring rubric prompt
SCORING_PROMPT = """You are an expert DSA (Data Structures & Algorithms) code reviewer.

PROBLEM:
{problem_description}

STUDENT'S CODE ({language}):
```
{source_code}
```

TEST RESULTS:
- Tests passed: {tests_passed}/{tests_total}
- Execution time: {execution_time_ms}ms
- Memory used: {memory_used_kb}KB

TASK: Evaluate this code on the following dimensions. Return ONLY valid JSON.

SCORING RUBRIC:
1. correctness (0-40): Based on test pass rate. Full marks = all tests pass.
2. code_quality (0-25): Clean code, proper variable names, no redundancy, good structure.
3. complexity_analysis (0-20): Is the algorithm optimal? Identify time/space complexity.
   - 20 = optimal solution
   - 15 = acceptable but not optimal
   - 10 = brute force that works
   - 5 = inefficient
   - 0 = wrong approach
4. style_readability (0-15): Indentation, comments, naming conventions, modularity.

OUTPUT FORMAT (JSON only, no extra text):
{{
  "total_score": <sum of all dimensions, 0-100>,
  "correctness": {{
    "score": <0-40>,
    "feedback": "<one sentence>"
  }},
  "code_quality": {{
    "score": <0-25>,
    "feedback": "<one sentence>"
  }},
  "complexity_analysis": {{
    "score": <0-20>,
    "time_complexity": "<e.g. O(n log n)>",
    "space_complexity": "<e.g. O(n)>",
    "feedback": "<one sentence>"
  }},
  "style_readability": {{
    "score": <0-15>,
    "feedback": "<one sentence>"
  }},
  "overall_feedback": "<2-3 sentences summarizing strengths and areas to improve>",
  "suggestions": ["<improvement 1>", "<improvement 2>"]
}}
"""


async def score_submission(
    problem_description: str,
    source_code: str,
    language: str,
    tests_passed: int,
    tests_total: int,
    execution_time_ms: int = 0,
    memory_used_kb: int = 0,
) -> Optional[Dict]:
    """
    Call the LLM to produce a structured code review score.

    Returns the parsed JSON rubric or None on failure.
    """
    settings = get_settings()

    prompt = SCORING_PROMPT.format(
        problem_description=problem_description[:2000],
        language=language,
        source_code=source_code[:4000],
        tests_passed=tests_passed,
        tests_total=tests_total,
        execution_time_ms=execution_time_ms,
        memory_used_kb=memory_used_kb,
    )

    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.2,
            "num_predict": 1024,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json=payload,
            )
            if resp.status_code != 200:
                logger.error(f"Ollama returned {resp.status_code}: {resp.text[:200]}")
                return _fallback_score(tests_passed, tests_total)

            raw = resp.json().get("response", "")
            try:
                result = json.loads(raw)
                # Validate structure
                if "total_score" not in result:
                    result["total_score"] = _calculate_total(result)
                return result
            except json.JSONDecodeError:
                logger.warning("AI scorer returned non-JSON, using fallback")
                return _fallback_score(tests_passed, tests_total)

    except Exception as e:
        logger.error(f"AI scoring failed: {e}")
        return _fallback_score(tests_passed, tests_total)


def _calculate_total(result: Dict) -> int:
    total = 0
    for key in ("correctness", "code_quality", "complexity_analysis", "style_readability"):
        section = result.get(key, {})
        if isinstance(section, dict):
            total += section.get("score", 0)
    return total


def _fallback_score(tests_passed: int, tests_total: int) -> Dict:
    """Deterministic fallback when AI is unavailable."""
    correctness = int((tests_passed / max(tests_total, 1)) * 40)
    return {
        "total_score": correctness + 15,  # Give base quality/style points
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
        "overall_feedback": "Automated scoring based on test results only. AI review was unavailable.",
        "suggestions": [],
        "ai_available": False,
    }
