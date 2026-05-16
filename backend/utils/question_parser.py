"""
Question Parser
---------------
Turns line-level PDF blocks into clean, structured questions.

Pipeline
  1. Pre-clean:
       - drop page headers / footers / page numbers / noise
       - detect and separate the "Answer Key" section
  2. Segment:
       - group lines into one "segment" per question using
         numbered-question start patterns (1., Q1., Q1), (1), [1], etc.)
  3. Parse each segment:
       - split out inline MCQ options
         (e.g. "(A) Apple (B) Banana (C) Cherry (D) Date")
       - detect inline answer markers
         (e.g. "Ans: B", "Answer - Paris", "Correct: C")
       - extract marks tags like "[2 marks]"
  4. Merge the separate Answer Key into the corresponding questions.

The parser is defensive: if something looks malformed it lowers the
confidence score instead of crashing.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------- #
# Data classes
# --------------------------------------------------------------------- #
class DetectedQuestionType(str, Enum):
    MCQ = "mcq"
    TRUE_FALSE = "true_false"
    FILL_BLANKS = "fill_blanks"
    SHORT_ANSWER = "short_answer"
    ESSAY = "essay"
    MATCHING = "matching"
    UNKNOWN = "unknown"


@dataclass
class ParsedQuestion:
    question_number: int
    question_text: str
    question_type: DetectedQuestionType
    options: Dict[str, str] = field(default_factory=dict)
    correct_answer: Optional[str] = None
    marks: Optional[int] = None
    page_number: Optional[int] = None
    confidence: float = 0.0


# --------------------------------------------------------------------- #
# Regex library (compiled once)
# --------------------------------------------------------------------- #
# A line that STARTS a question. Captures (number, rest-of-text).
_RE_QUESTION_START = re.compile(
    r"""^\s*
        (?:Q(?:uestion)?\s*\.?\s*|Ques\s*\.?\s*)?      # optional Q/Question/Ques
        (?:\(\s*(\d{1,3})\s*\)|\[\s*(\d{1,3})\s*\]|(\d{1,3}))  # number
        \s*[\.\):\-\]]\s+                               # separator
        (.*)$
    """,
    re.VERBOSE,
)

# Inline option splitter. Works for:
#   A) foo   A. foo   (A) foo   A: foo   a) foo   (a) foo
_RE_INLINE_OPTION = re.compile(
    r"""(?:(?<=\s)|^|(?<=[\.\)\]]))   # must be at start or after space/punct
        (?:\(([A-Ha-h])\)|([A-Ha-h])[\)\.:])  # (A) or A) or A. or A:
        \s+
    """,
    re.VERBOSE,
)

# Standalone option line: "A) option text" or "(a) option text"
_RE_OPTION_LINE = re.compile(
    r"""^\s*
        (?:\(([A-Ha-h])\)|([A-Ha-h])[\)\.:])   # option letter
        \s+(.+)$
    """,
    re.VERBOSE,
)

# Answer markers inside / after a question.
#   "Answer: B", "Ans. C", "Correct answer - Paris", "Solution: 42"
_RE_INLINE_ANSWER = re.compile(
    r"""\b(?:Answer|Ans|Correct\s+Answer|Solution|Correct|Key)
        \s*[\.\:\-–—]\s*
        ([^\n]+?)
        \s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Marks tag: [2 marks], (3 pts)
_RE_MARKS = re.compile(
    r"[\[\(]\s*(\d{1,3})\s*(?:marks?|pts?|points?|m)\s*[\]\)]",
    re.IGNORECASE,
)

# Answer-Key section header (rest of document becomes answer key)
_RE_ANSWER_KEY_HEADER = re.compile(
    r"^\s*(?:answers?\s*key|answer\s*sheet|answers?|solutions?|key)\s*[:\-]?\s*$",
    re.IGNORECASE,
)

# Answer-key line inside the key section:
#   "1. B"   "1) B"   "Q1 - B"   "1: Paris"
_RE_ANSWER_KEY_ENTRY = re.compile(
    r"""^\s*
        (?:Q(?:uestion)?\s*\.?\s*)?
        (\d{1,3})
        \s*[\.\)\:\-]\s*
        (.+?)\s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Noise patterns: page numbers, copyright, URLs
_RE_NOISE = [
    re.compile(r"^page\s*\d+\s*(of\s*\d+)?\s*$", re.IGNORECASE),
    re.compile(r"^\-\s*\d+\s*\-$"),
    re.compile(r"^\d+\s*$"),
    re.compile(r"^©.*$"),
    re.compile(r"^copyright\b.*$", re.IGNORECASE),
    re.compile(r"^all rights reserved\s*\.?$", re.IGNORECASE),
    re.compile(r"^https?://\S+$"),
    re.compile(r"^www\.\S+$"),
]

# True/false indicators
_RE_TRUE_FALSE = re.compile(
    r"\b(true\s*/\s*or\s+false|true\s*/\s*false|t\s*/\s*f|state\s+(?:if|whether)\b)",
    re.IGNORECASE,
)

# Fill-in-the-blanks indicators
_RE_BLANK = re.compile(r"(_{3,}|\.{4,}|<\s*blank\s*>|\[\s*_+\s*\])", re.IGNORECASE)

# Essay markers
_ESSAY_KEYWORDS = (
    "discuss", "explain", "describe", "analyze", "analyse",
    "evaluate", "compare", "elaborate", "justify", "illustrate",
)


# --------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------- #
class QuestionParser:
    """Convert line-blocks into ParsedQuestion objects."""

    def __init__(self) -> None:
        pass

    # --------- Public API --------- #
    def parse(self, text_blocks: List[Dict]) -> List[ParsedQuestion]:
        lines = self._blocks_to_lines(text_blocks)
        lines = self._strip_noise(lines)
        body_lines, answer_key = self._split_answer_key(lines)
        segments = self._segment_questions(body_lines)

        parsed: List[ParsedQuestion] = []
        for idx, seg in enumerate(segments, start=1):
            q = self._parse_segment(seg, idx)
            if q:
                parsed.append(q)

        if answer_key:
            self._apply_answer_key(parsed, answer_key)

        logger.info(
            f"Parsed {len(parsed)} questions "
            f"(answer key entries: {len(answer_key)})"
        )
        return parsed

    def parse_raw_text(
        self, raw_text: str, topic: str = "Extracted Questions"
    ) -> List[Dict]:
        """Convenience wrapper: accept plain text, return question-bank dicts."""
        fake_blocks = [
            {"text": line, "page": 1, "line_no": i}
            for i, line in enumerate(raw_text.splitlines(), start=1)
            if line.strip()
        ]
        parsed = self.parse(fake_blocks)
        return [self._to_bank_dict(q, topic) for q in parsed]

    # --------- Stage 1: line prep + noise --------- #
    @staticmethod
    def _blocks_to_lines(blocks: List[Dict]) -> List[Dict]:
        out: List[Dict] = []
        for b in blocks:
            text = (b.get("text") or "").strip()
            if not text:
                continue
            # Collapse multiple internal whitespace to single space.
            text = re.sub(r"[ \t]+", " ", text)
            out.append({
                "text": text,
                "page": b.get("page", 1),
                "line_no": b.get("line_no"),
            })
        return out

    @staticmethod
    def _strip_noise(lines: List[Dict]) -> List[Dict]:
        cleaned: List[Dict] = []
        for ln in lines:
            txt = ln["text"].strip()
            if not txt:
                continue
            if any(p.match(txt) for p in _RE_NOISE):
                continue
            cleaned.append(ln)
        return cleaned

    # --------- Stage 2: answer-key isolation --------- #
    @staticmethod
    def _split_answer_key(
        lines: List[Dict],
    ) -> Tuple[List[Dict], Dict[int, str]]:
        """
        If the document contains an "Answer Key" section, split it off
        and parse each "N. X" line into {question_number: answer_text}.
        """
        header_idx = -1
        for i, ln in enumerate(lines):
            if _RE_ANSWER_KEY_HEADER.match(ln["text"]):
                # Only treat it as the answer key when it's near the end
                # AND at least 2 following lines look like "N. X".
                tail = lines[i + 1: i + 12]
                matches = sum(
                    1 for t in tail if _RE_ANSWER_KEY_ENTRY.match(t["text"])
                )
                if matches >= 2:
                    header_idx = i
                    break

        if header_idx == -1:
            return lines, {}

        body = lines[:header_idx]
        key_lines = lines[header_idx + 1:]

        answers: Dict[int, str] = {}
        for ln in key_lines:
            m = _RE_ANSWER_KEY_ENTRY.match(ln["text"])
            if not m:
                continue
            try:
                q_num = int(m.group(1))
            except ValueError:
                continue
            answers[q_num] = m.group(2).strip().rstrip(".")

        logger.info(f"Answer-key section detected with {len(answers)} entries")
        return body, answers

    # --------- Stage 3: segment by question number --------- #
    @staticmethod
    def _segment_questions(lines: List[Dict]) -> List[Dict]:
        segments: List[Dict] = []
        current: Optional[Dict] = None

        for ln in lines:
            m = _RE_QUESTION_START.match(ln["text"])
            if m:
                number = next(g for g in m.groups()[:3] if g)
                rest = m.group(4)
                if current:
                    segments.append(current)
                current = {
                    "question_number": int(number),
                    "page": ln["page"],
                    "lines": [rest.strip()] if rest.strip() else [],
                }
            elif current is not None:
                current["lines"].append(ln["text"])
            # Lines before the first question are ignored.

        if current:
            segments.append(current)
        return segments

    # --------- Stage 4: per-segment parsing --------- #
    def _parse_segment(
        self, segment: Dict, fallback_number: int
    ) -> Optional[ParsedQuestion]:
        lines: List[str] = segment.get("lines", [])
        if not lines:
            return None

        # 1. Remove any inline answer marker, remember the answer it stated.
        inline_answer: Optional[str] = None
        cleaned_lines: List[str] = []
        for ln in lines:
            m = _RE_INLINE_ANSWER.search(ln)
            if m:
                inline_answer = m.group(1).strip().rstrip(".")
                ln = ln[: m.start()].rstrip()
                if not ln:
                    continue
            cleaned_lines.append(ln)

        # 2. Extract marks tag (then strip it from the text).
        marks: Optional[int] = None
        stripped_lines: List[str] = []
        for ln in cleaned_lines:
            m = _RE_MARKS.search(ln)
            if m:
                try:
                    marks = int(m.group(1))
                except ValueError:
                    pass
                ln = _RE_MARKS.sub("", ln).strip()
                if not ln:
                    continue
            stripped_lines.append(ln)

        # 3. Split question body from options.
        question_text, options = self._split_question_and_options(stripped_lines)
        if not question_text or len(question_text) < 3:
            return None

        q_type = self._detect_type(question_text, options)

        # 4. Validate the inline answer against detected options.
        correct_answer = self._normalise_answer(inline_answer, options, q_type)

        return ParsedQuestion(
            question_number=segment.get("question_number", fallback_number),
            question_text=question_text,
            question_type=q_type,
            options=options,
            correct_answer=correct_answer,
            marks=marks,
            page_number=segment.get("page"),
            confidence=self._confidence(question_text, options, q_type),
        )

    # --------- Option splitting --------- #
    @staticmethod
    def _split_question_and_options(
        lines: List[str],
    ) -> Tuple[str, Dict[str, str]]:
        """
        Handles three layouts:
          * options on separate lines
          * all options on one line ("(A) x (B) y (C) z")
          * mixed (question + first option on same line)
        """
        joined = "\n".join(lines).strip()

        # Quick short-circuit: do we even have option markers?
        has_markers = bool(_RE_OPTION_LINE.search(joined) or _RE_INLINE_OPTION.search(joined))
        if not has_markers:
            return re.sub(r"\s+", " ", joined).strip(), {}

        # Walk lines one at a time. For each line, first see whether it
        # has an inline option marker; if so, the text BEFORE the first
        # marker belongs to the question / previous option, and each
        # marker starts a new option until the next marker / EOL.
        question_parts: List[str] = []
        options: Dict[str, str] = {}
        current_letter: Optional[str] = None
        current_buffer: List[str] = []

        def flush_current() -> None:
            nonlocal current_letter, current_buffer
            if current_letter is not None:
                text = " ".join(current_buffer).strip()
                text = re.sub(r"\s+", " ", text)
                if text:
                    options[current_letter.upper()] = text
            current_letter = None
            current_buffer = []

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue

            # Find every inline option marker in the line.
            matches = list(_RE_INLINE_OPTION.finditer(line))
            if not matches:
                # No markers on this line - belongs to whatever we're building.
                if current_letter is None:
                    question_parts.append(line)
                else:
                    current_buffer.append(line)
                continue

            # Text before the first marker belongs to question / previous option.
            first_start = matches[0].start()
            leading = line[:first_start].strip()
            if leading:
                if current_letter is None:
                    question_parts.append(leading)
                else:
                    current_buffer.append(leading)

            # Iterate markers and split the remaining text accordingly.
            for idx, m in enumerate(matches):
                letter = m.group(1) or m.group(2)
                seg_start = m.end()
                seg_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(line)
                seg_text = line[seg_start:seg_end].strip()

                flush_current()
                current_letter = letter
                if seg_text:
                    current_buffer.append(seg_text)

        flush_current()

        question_text = re.sub(r"\s+", " ", " ".join(question_parts)).strip()

        # Sanity: MCQ needs >=2 options; otherwise treat all extracted "options"
        # as part of the question (i.e. misdetection).
        if len(options) < 2:
            merged = question_text
            for letter, val in options.items():
                merged = f"{merged} ({letter}) {val}".strip()
            return re.sub(r"\s+", " ", merged).strip(), {}

        return question_text, options

    # --------- Type detection --------- #
    @staticmethod
    def _detect_type(question_text: str, options: Dict[str, str]) -> DetectedQuestionType:
        text = question_text.lower()

        if len(options) >= 2:
            if len(options) == 2:
                vals = {v.lower().strip() for v in options.values()}
                if vals <= {"true", "false", "t", "f"}:
                    return DetectedQuestionType.TRUE_FALSE
            return DetectedQuestionType.MCQ

        if _RE_TRUE_FALSE.search(question_text):
            return DetectedQuestionType.TRUE_FALSE
        if _RE_BLANK.search(question_text):
            return DetectedQuestionType.FILL_BLANKS

        for kw in _ESSAY_KEYWORDS:
            if kw in text:
                return DetectedQuestionType.ESSAY

        return DetectedQuestionType.SHORT_ANSWER

    # --------- Answer normalisation --------- #
    @staticmethod
    def _normalise_answer(
        raw: Optional[str],
        options: Dict[str, str],
        q_type: DetectedQuestionType,
    ) -> Optional[str]:
        if not raw:
            return None
        raw = raw.strip().rstrip(".").strip()

        if q_type == DetectedQuestionType.MCQ and options:
            # Accept forms: "B", "(B)", "Option B", "B - Paris"
            m = re.match(r"^\(?([A-Ha-h])\)?\b", raw)
            if m and m.group(1).upper() in options:
                return m.group(1).upper()
            # Match by option VALUE (case-insensitive)
            for letter, val in options.items():
                if val.strip().lower() == raw.lower():
                    return letter
            return raw
        return raw

    # --------- Answer-key merging --------- #
    @staticmethod
    def _apply_answer_key(
        questions: List[ParsedQuestion], key: Dict[int, str]
    ) -> None:
        for q in questions:
            if q.correct_answer:
                continue
            ans = key.get(q.question_number)
            if not ans:
                continue
            q.correct_answer = QuestionParser._normalise_answer(
                ans, q.options, q.question_type
            )

    # --------- Confidence score --------- #
    @staticmethod
    def _confidence(
        question_text: str,
        options: Dict[str, str],
        q_type: DetectedQuestionType,
    ) -> float:
        score = 0.0
        if len(question_text) >= 15:
            score += 0.3
        if question_text.endswith("?"):
            score += 0.15

        if q_type == DetectedQuestionType.MCQ:
            if len(options) >= 4:
                score += 0.4
            elif len(options) >= 2:
                score += 0.2
        else:
            score += 0.3

        if not re.search(r"[^\x00-\x7F]", question_text):
            score += 0.1

        return round(min(score, 1.0), 3)

    # --------- Bank-dict conversion --------- #
    @staticmethod
    def _to_bank_dict(q: ParsedQuestion, topic: str) -> Dict:
        return {
            "question_text": q.question_text,
            "question_type": q.question_type.value,
            "topic": topic,
            "points": q.marks or 1,
            "status": "draft",
            "question_data": {
                "options": q.options,
                "correct_answer": q.correct_answer,
            },
            "confidence": q.confidence,
        }
