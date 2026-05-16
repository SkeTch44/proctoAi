"""
Question Sanitizer
------------------
Central place to clean every question before it's saved / shown,
regardless of source (PDF scan, RAG+LLM, pure AI).

Why: LLMs hallucinate stray "Answer: B" lines, numbering like "1.",
trailing explanations, unbalanced options, duplicates, and so on.
This module normalises the shape so students always see clean
questions in the ExamRoom.
"""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------- #
# Patterns
# --------------------------------------------------------------------- #
_RE_LEADING_NUMBER = re.compile(
    r"^\s*(?:Q(?:uestion)?\s*\.?\s*)?"
    r"(?:\(\s*\d{1,3}\s*\)|\[\s*\d{1,3}\s*\]|\d{1,3})"
    r"\s*[\.\):\-\]]\s*",
    re.IGNORECASE,
)

_RE_ANSWER_TAIL = re.compile(
    r"""
    (?:[\r\n]|\s{2,})?
    \s*
    (?:Answer|Ans|Correct\s+Answer|Solution|Correct|Key)
    \s*[\.\:\-–—]\s*
    .+?$
    """,
    re.IGNORECASE | re.VERBOSE | re.DOTALL,
)

_RE_EXPLANATION_TAIL = re.compile(
    r"""
    (?:[\r\n]|\s{1,})
    (?:Explanation|Rationale|Reason|Justification|Note|Hint)
    \s*[\.\:\-–—]\s*
    .+?$
    """,
    re.IGNORECASE | re.VERBOSE | re.DOTALL,
)

_RE_MULTISPACE = re.compile(r"\s+")


# --------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------- #
def _clean_text(text: Any) -> str:
    if text is None:
        return ""
    text = str(text)
    # Strip control chars
    text = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]", "", text)
    # Normalise whitespace
    text = _RE_MULTISPACE.sub(" ", text).strip()
    return text


def _strip_leading_number(text: str) -> str:
    return _RE_LEADING_NUMBER.sub("", text, count=1).strip()


def _strip_answer_and_explanation(text: str) -> Tuple[str, Optional[str]]:
    """Remove stray 'Answer: X' / 'Explanation: ...' trailing segments.

    Returns (clean_text, extracted_answer or None).
    """
    extracted_answer: Optional[str] = None

    m = _RE_ANSWER_TAIL.search(text)
    if m:
        raw = m.group(0)
        # pull just the value after the marker
        mm = re.search(
            r"(?:Answer|Ans|Correct\s+Answer|Solution|Correct|Key)"
            r"\s*[\.\:\-–—]\s*([^\r\n]+)",
            raw,
            re.IGNORECASE,
        )
        if mm:
            extracted_answer = mm.group(1).strip().rstrip(".")
        text = text[: m.start()].rstrip()

    text = _RE_EXPLANATION_TAIL.sub("", text).rstrip()
    return text.strip(), extracted_answer


def _normalise_options(raw: Any) -> Dict[str, str]:
    """Accept list / dict / weird shapes and return {"A": "...", "B": "..."}."""
    if not raw:
        return {}

    options: Dict[str, str] = {}

    if isinstance(raw, dict):
        for k, v in raw.items():
            key = str(k).strip().upper()
            # Allow keys like "(A)" or "A)" -> "A"
            m = re.match(r"^\(?([A-H])\)?$", key)
            if m:
                key = m.group(1)
            val = _clean_text(v)
            # Strip leading "A) " if present
            val = re.sub(r"^\s*\(?[A-Ha-h]\)?\s*[\.\):\-]\s*", "", val)
            if val:
                options[key] = val

    elif isinstance(raw, list):
        for i, val in enumerate(raw):
            if i >= 8:
                break
            text = _clean_text(val)
            text = re.sub(r"^\s*\(?[A-Ha-h]\)?\s*[\.\):\-]\s*", "", text)
            if text:
                options[chr(65 + i)] = text

    return options


def _normalise_answer(
    raw: Any, options: Dict[str, str]
) -> Optional[str]:
    if raw is None:
        return None
    ans = _clean_text(raw).rstrip(".")
    if not ans:
        return None

    if options:
        # "A", "(A)", "Option A", "A - Paris"
        m = re.match(r"^\(?([A-H])\)?\b", ans, re.IGNORECASE)
        if m:
            letter = m.group(1).upper()
            if letter in options:
                return letter
        # Match by value text
        for letter, val in options.items():
            if val.strip().lower() == ans.lower():
                return letter
    return ans


# --------------------------------------------------------------------- #
# Public sanitize API
# --------------------------------------------------------------------- #
def sanitize_question(q: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Normalise a single question dict (shape produced by PDF scan / LLM).

    Returns None if the question is too broken to salvage.
    """
    if not isinstance(q, dict):
        return None

    text = _clean_text(
        q.get("question_text")
        or q.get("question")
        or q.get("text")
        or ""
    )
    text = _strip_leading_number(text)
    text, tail_answer = _strip_answer_and_explanation(text)

    if len(text) < 5:
        return None

    q_type = _clean_text(q.get("question_type") or q.get("type") or "mcq").lower()
    if q_type in ("multiple_choice", "multi_choice", "mcq_4"):
        q_type = "mcq"

    # Options
    raw_options = (
        q.get("options")
        or (q.get("question_data") or {}).get("options")
    )
    options = _normalise_options(raw_options)

    # Answer
    raw_answer = (
        q.get("correct_answer")
        or q.get("answer")
        or (q.get("question_data") or {}).get("correct_answer")
        or (q.get("question_data") or {}).get("answer")
        or tail_answer
    )
    answer = _normalise_answer(raw_answer, options)

    # Refine type based on what we actually found
    if q_type == "mcq" and len(options) < 2:
        q_type = "short_answer"
    if len(options) == 2:
        lower_vals = {v.strip().lower() for v in options.values()}
        if lower_vals <= {"true", "false", "t", "f"}:
            q_type = "true_false"

    explanation = _clean_text(
        q.get("explanation")
        or (q.get("question_data") or {}).get("explanation")
        or ""
    )

    try:
        points = int(q.get("points") or q.get("marks") or 1)
    except (TypeError, ValueError):
        points = 1

    difficulty = _clean_text(q.get("difficulty") or "medium").lower()
    if difficulty not in ("easy", "medium", "hard", "expert"):
        difficulty = "medium"

    clean: Dict[str, Any] = {
        "question_text": text,
        "question_type": q_type,
        "topic": _clean_text(q.get("topic") or ""),
        "difficulty": difficulty,
        "points": max(1, points),
        "status": _clean_text(q.get("status") or "draft"),
        "question_data": {
            "options": options,
            "correct_answer": answer,
            "explanation": explanation,
        },
        "explanation": explanation,
    }

    # preserve metadata if present
    if "metadata" in q and isinstance(q["metadata"], dict):
        clean["metadata"] = q["metadata"]

    # preserve confidence if present
    if "confidence" in q:
        try:
            clean["confidence"] = float(q["confidence"])
        except (TypeError, ValueError):
            pass

    return clean


def sanitize_questions(raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Clean a batch and drop exact duplicates (by normalised text)."""
    seen: set = set()
    out: List[Dict[str, Any]] = []

    for q in raw or []:
        clean = sanitize_question(q)
        if not clean:
            continue
        fingerprint = hashlib.sha1(
            clean["question_text"].lower().encode("utf-8")
        ).hexdigest()
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        out.append(clean)

    logger.info(f"Sanitised {len(out)}/{len(raw or [])} questions")
    return out


# Convenience flag useful for callers that want a minimal MCQ validator
def is_valid_mcq(q: Dict[str, Any]) -> bool:
    qd = q.get("question_data") or {}
    options = qd.get("options") or {}
    return bool(
        q.get("question_type") == "mcq"
        and len(options) >= 2
        and q.get("question_text")
    )
