import json
import logging 
from typing import Dict, Any, List, Tuple, Optional
from sentence_transformers import SentenceTransformer, util
import numpy as np
from difflib import SequenceMatcher
from pathlib import Path

logger = logging.getLogger(__name__)

class GradingEngine:
    """
    Automated grading engine supporting multiple question types:
     - Multiple Choice Questions (MCQ)
     - True/False Questions 
     - Short Answer Questions
     - Fill in the Blanks Questions 
     - Matching 
     - Essay 
     Uses semantic similarity (Sentence Transformers) for open ended responses
     and rule-based for closed ended types.
     
     Enhanced with:
     - Partial credit buckets based on similarity thresholds
     - Cheating detection (exact match, AI paraphrasing)
    """
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2', rubric_path: Optional[str] = None):
        self._model_name = model_name
        self._sim_model = None  # Lazy-loaded
        
        # Load grading rubric configuration
        if rubric_path is None:
            rubric_path = Path(__file__).parent / 'grading_rubric.json'
        
        try:
            with open(rubric_path, 'r') as f:
                self.rubric = json.load(f)
            logger.info(f"Loaded grading rubric from {rubric_path}")
        except Exception as e:
            logger.warning(f"Failed to load rubric config: {e}. Using defaults.")
            self.rubric = self._get_default_rubric()
            
    @property
    def sim_model(self):
        """Lazy-load SentenceTransformer model on first use"""
        if self._sim_model is None:
            try:
                logger.info(f"Lazy-loading semantic model: {self._model_name}")
                self._sim_model = SentenceTransformer(self._model_name)
            except Exception as e:
                logger.error(f"Failed to load semantic model: {e}")
        return self._sim_model
    
    def _get_default_rubric(self) -> Dict[str, Any]:
        """Fallback rubric if config file not found"""
        return {
            "thresholds": {
                "short_answer": {
                    "excellent": {"min_similarity": 0.85, "credit_percentage": 100},
                    "good": {"min_similarity": 0.65, "credit_percentage": 75},
                    "partial": {"min_similarity": 0.40, "credit_percentage": 50},
                    "insufficient": {"min_similarity": 0.0, "credit_percentage": 0}
                },
                "essay": {
                    "excellent": {"min_similarity": 0.80, "credit_percentage": 100},
                    "good": {"min_similarity": 0.60, "credit_percentage": 75},
                    "partial": {"min_similarity": 0.35, "credit_percentage": 50},
                    "insufficient": {"min_similarity": 0.0, "credit_percentage": 0}
                }
            },
            "cheating_detection": {
                "exact_match_threshold": 0.98,
                "exact_match_min_words": 15,
                "ai_paraphrase": {
                    "high_semantic_threshold": 0.90,
                    "low_lexical_threshold": 0.40
                }
            }
        }
    
    def _calculate_lexical_similarity(self, text1: str, text2: str) -> float:
        """Calculate lexical similarity using SequenceMatcher (0.0 to 1.0)"""
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    
    def _detect_cheating_flags(self, user_answer: str, sample_answer: str, semantic_score: float) -> List[str]:
        """
        Detect potential cheating patterns.
        Returns list of flags: ['EXACT_MATCH'], ['AI_PARAPHRASE_SUSPECTED'], or []
        """
        flags = []
        
        # Exact match detection
        exact_threshold = self.rubric['cheating_detection']['exact_match_threshold']
        min_words = self.rubric['cheating_detection']['exact_match_min_words']
        
        lexical_sim = self._calculate_lexical_similarity(user_answer, sample_answer)
        word_count = len(user_answer.split())
        
        if lexical_sim >= exact_threshold and word_count >= min_words:
            flags.append('EXACT_MATCH')
        
        # AI Paraphrasing detection
        ai_config = self.rubric['cheating_detection']['ai_paraphrase']
        high_sem_threshold = ai_config['high_semantic_threshold']
        low_lex_threshold = ai_config['low_lexical_threshold']
        
        if semantic_score >= high_sem_threshold and lexical_sim < low_lex_threshold:
            flags.append('AI_PARAPHRASE_SUSPECTED')
        
        return flags 

    def grade_exam(self, questions: List[Dict[str, Any]], answers: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Grade a full exam.
        
        Args:
            questions: list of questions dicts(id, type, points, etc.)
            answers: mapping from question id (str) to user answer
            metadata: Optional dictionary containing session_id, exam_id, candidate_id, etc.
            
        Returns:
            Summary dictionary with scores, details, and metadata.
        """                
        total_score = 0.0 
        max_score = 0.0
        details = []

        for q in questions:
            qid = str(q.get('id'))
            max_points = q.get('points', 1)
            max_score += max_points
            user_ans = answers.get(qid, None)

            score, feedback = self.grade_question(q, user_ans)
            total_score += score 
            details.append({
                'id': qid,
                'type': q.get('type'),
                'max_points': max_points,
                'score': score,
                'feedback': feedback
            })     
        
        percentage = (total_score / max_score * 100) if max_score else 0  
        
        result = {
            'total_score': total_score,
            'max_score': max_score,
            'percentage': round(percentage, 2),
            'details': details
        }
        
        # Merge metadata into result if provided
        if metadata:
            result.update(metadata)
            
        return result

    def grade_question(self, question: Dict[str, Any], answer: Any) -> Tuple[float, str]:
        """
        Grade an individual question based on its type. Returns (score, feedback).
        """
        qtype = question.get('type')
        if qtype == 'mcq':
            return self._grade_mcq(question, answer)
        if qtype == 'true_false':
            return self._grade_true_false(question, answer)
        if qtype == 'short_answer':
            return self._grade_short_answer(question, answer)
        if qtype == 'fill_blanks':
            return self._grade_fill_blanks(question, answer)
        if qtype == 'essay':
            return self._grade_essay(question, answer)
        
        # default fallback
        return 0.0, "unsupported question type"
    
    def _grade_mcq(self, q: Dict, ans: str) -> Tuple[float, str]:
        correct = q.get('correct_answer', '').strip().upper()
        user = (ans or '').strip().upper()
        if user == correct:
            return q.get('points', 1), "Correct"
        return 0.0, f"Incorrect. Correct answer: {correct}."
    
    def _grade_true_false(self, q: Dict, ans: Any) -> Tuple[float, str]:
        correct = bool(q.get('correct_answer', False))
        user = True if str(ans).lower() in ['true', 't', '1', 'yes'] else False
        if user == correct:
            return q.get('points', 1), "Correct."
        return 0.0, f"Incorrect. Correct answer: {correct}."

    def _grade_short_answer(self, q: Dict, ans: str) -> Tuple[float, str]:
        """Grade short answer with partial credit buckets and cheating detection"""
        sample = q.get('sample_answer', '')
        if not sample or not ans:
            return 0.0, "No sample answer or user answer provided"
        
        max_points = q.get('points', 2)
        
        if self.sim_model:
            # Calculate semantic similarity
            score = util.pytorch_cos_sim(
                *self.sim_model.encode([sample, ans], convert_to_tensor=True)
            ).item()
            normalized = min(max(score, 0.0), 1.0)
            
            # Detect cheating flags
            flags = self._detect_cheating_flags(ans, sample, normalized)
            
            # Apply partial credit buckets
            thresholds = self.rubric['thresholds']['short_answer']
            credit_pct = 0
            
            if normalized >= thresholds['excellent']['min_similarity']:
                credit_pct = thresholds['excellent']['credit_percentage']
            elif normalized >= thresholds['good']['min_similarity']:
                credit_pct = thresholds['good']['credit_percentage']
            elif normalized >= thresholds['partial']['min_similarity']:
                credit_pct = thresholds['partial']['credit_percentage']
            else:
                credit_pct = thresholds['insufficient']['credit_percentage']
            
            points = (credit_pct / 100.0) * max_points
            
            # Build feedback
            feedback_parts = [f"Similarity: {normalized:.2f}", f"Credit: {credit_pct}%"]
            if flags:
                feedback_parts.append(f"Flags: {', '.join(flags)}")
            
            feedback = " | ".join(feedback_parts)
            
            return round(points, 2), feedback
        
        # Fallback: keyword matching
        overlap = len(set(sample.lower().split()) & set(ans.lower().split()))
        ratio = overlap / max(len(sample.split()), 1)
        points = ratio * max_points
        feedback = f"Keyword match: {ratio:.2f}"
        return round(points, 2), feedback

    def _grade_fill_blanks(self, q: Dict, ans: Any) -> Tuple[float, str]:
        correct = [b.lower() for b in q.get('blanks', [])]
        user = [u.strip().lower() for u in (ans or [])]
        if not correct or not user:
            return 0.0, "No blanks or answers provided"
        right = sum(1 for u, c in zip(user, correct) if u == c) 
        ratio = right / len(correct)
        points = ratio * q.get('points', 1)
        feedback = f"{right}/{len(correct)} correct"
        return round(points, 2), feedback
    
    def _grade_essay(self, q: Dict, ans: str) -> Tuple[float, str]:
        """Grade essay with partial credit buckets and cheating detection"""
        sample = q.get('sample_answer', '')
        if not ans:
            return 0.0, "No answer provided"
        
        max_points = q.get('points', 5)
        
        # Length check (20% of score)
        words = len(ans.split())
        ideal_length = q.get('ideal_length', 200)
        length_score = min(words / ideal_length, 1.0) * 0.2
        
        # Semantic check (80% of score)
        sem_score = 0.0
        flags = []
        normalized = 0.0
        
        if self.sim_model and sample:
            try:
                sem = util.pytorch_cos_sim(
                    *self.sim_model.encode([sample, ans], convert_to_tensor=True)
                ).item()
                normalized = min(max(sem, 0.0), 1.0)
                
                # Detect cheating flags
                flags = self._detect_cheating_flags(ans, sample, normalized)
                
                # Apply partial credit buckets for semantic component
                thresholds = self.rubric['thresholds']['essay']
                credit_pct = 0
                
                if normalized >= thresholds['excellent']['min_similarity']:
                    credit_pct = thresholds['excellent']['credit_percentage']
                elif normalized >= thresholds['good']['min_similarity']:
                    credit_pct = thresholds['good']['credit_percentage']
                elif normalized >= thresholds['partial']['min_similarity']:
                    credit_pct = thresholds['partial']['credit_percentage']
                else:
                    credit_pct = thresholds['insufficient']['credit_percentage']
                
                sem_score = (credit_pct / 100.0) * 0.8
                
            except Exception as e:
                logger.warning(f"Semantic model error: {e}")
        
        total = (length_score + sem_score) * max_points
        
        # Build feedback
        feedback_parts = [
            f"Length: {length_score:.2f}",
            f"Semantic: {sem_score:.2f}",
            f"Similarity: {normalized:.2f}"
        ]
        if flags:
            feedback_parts.append(f"Flags: {', '.join(flags)}")
        
        feedback = " | ".join(feedback_parts)
        
        return round(total, 2), feedback
