import re
import random
import uuid
from typing import List, Dict, Any


class EnhancedQuestionGenerator:
    """
    Enhanced template-based question generator supporting:
      - MCQ
      - True/False
      - Short Answer
      - Fill-in-the-Blanks
      - Matching
      - Essay
    Easily extensible and AI-friendly.
    """

    def __init__(self):
        # Seed random for reproducibility if desired
        random.seed()

    def generate_questions(self, content: str, config: Dict[str, Any]) -> List[Dict]:
        """
        Generate questions based on configuration:
        config = {
          'mcq': {'count': 3, 'difficulty': 'easy'},
          'short_answer': {'count': 2, 'difficulty': 'medium'},
          ...
        }
        Returns a list of question dicts.
        """
        questions: List[Dict] = []
        qid = 1
        for qtype, opts in config.items():
            if not opts.get('enabled', False):
                continue
            for _ in range(opts.get('count', 1)):
                gen = getattr(self, f"_gen_{qtype}", None)
                if not gen:
                    continue
                q = gen(content, opts['difficulty'], qid)
                if q:
                    questions.append(q)
                    qid += 1
        return questions

    def _gen_mcq(self, content: str, difficulty: str, qid: int) -> Dict:
        topic = self._extract_topic(content)
        options = [
            f"A) Definition of {topic}",
            f"B) A different concept",
            f"C) Unrelated concept",
            f"D) None of the above"
        ]
        return {
            "id": qid,
            "type": "mcq",
            "question": f"What does '{topic}' refer to in the text?",
            "options": options,
            "correct_answer": "A",
            "explanation": f"'{topic}' is clearly defined in the passage.",
            "difficulty": difficulty,
            "points": 1
        }

    def _gen_true_false(self, content: str, difficulty: str, qid: int) -> Dict:
        topic = self._extract_topic(content)
        tf = random.choice([True, False])
        stmt = f"'{topic}' is a central theme in the text." if tf else f"'{topic}' is never mentioned."
        return {
            "id": qid,
            "type": "true_false",
            "question": f"True or False: {stmt}",
            "correct_answer": tf,
            "difficulty": difficulty,
            "points": 1
        }

    def _gen_short_answer(self, content: str, difficulty: str, qid: int) -> Dict:
        topic = self._extract_topic(content)
        return {
            "id": qid,
            "type": "short_answer",
            "question": f"Briefly explain the concept of '{topic}'.",
            "sample_answer": f"{topic} is described as a key topic in the content.",
            "difficulty": difficulty,
            "points": 2
        }

    def _gen_fill_blanks(self, content: str, difficulty: str, qid: int) -> Dict:
        words = re.findall(r"\b\w{5,}\b", content)
        blanks = random.sample(words, min(2, len(words))) if words else ["______"]
        snippet = content
        for w in blanks:
            snippet = snippet.replace(w, "______", 1)
        return {
            "id": qid,
            "type": "fill_blanks",
            "question": f"Fill in the blanks: {snippet[:100]}...",
            "blanks": blanks,
            "difficulty": difficulty,
            "points": 2
        }

    def _gen_matching(self, content: str, difficulty: str, qid: int) -> Dict:
        terms = [f"Term{i}" for i in range(1, 4)]
        defs = [f"Definition{i}" for i in range(1, 4)]
        pairs = dict(zip(terms, defs))
        return {
            "id": qid,
            "type": "matching",
            "question": "Match each term to its definition.",
            "matching_pairs": pairs,
            "difficulty": difficulty,
            "points": 3
        }

    def _gen_essay(self, content: str, difficulty: str, qid: int) -> Dict:
        topic = self._extract_topic(content)
        return {
            "id": qid,
            "type": "essay",
            "question": f"Discuss the implications of '{topic}' as described in the text.",
            "sample_answer": f"A thorough essay would explore how '{topic}' affects the main ideas.",
            "difficulty": difficulty,
            "points": 5
        }

    def _extract_topic(self, content: str) -> str:
        # Simple extraction: first substantive word
        words = re.findall(r"\b\w{4,}\b", content)
        return words[0].capitalize() if words else "Topic"