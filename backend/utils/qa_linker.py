
import numpy as np
import re
from typing import List, Dict, Any, Optional
from backend.utils.rag_engine import RAGEngine

class QALinker:
    """
    Deterministic Q-A linking using rules + semantic similarity.
    Pairs identified QUESTION chunks with ANSWER chunks.
    """
    
    def __init__(self):
        pass

    def link_questions_answers(
        self, 
        questions: List[Dict], 
        answers: List[Dict],
        rag: RAGEngine
    ) -> List[Dict]:
        """
        Link questions to their best matching answers.
        
        Returns:
        [
            {
                "question": {...},
                "answer": {...},
                "confidence": 0.92,
                "link_method": "semantic" | "structural" | "keyword"
            }
        ]
        """
        links = []
        
        # Pre-compute embeddings for efficiency if not already in chunk
        # Assuming RAGEngine can help or we use what we have. 
        # For accurate scoring, we need embeddings. 
        # If chunks came from RAG, they might have IDs we can look up, but here we likely have raw text.
        # Let's generate embeddings on the fly if needed, or assume RAG engine usage.
        
        if not questions:
            return []

        # Optimization: Batch encode all questions and answers
        q_texts = [q['text'] for q in questions]
        a_texts = [a['text'] for a in answers]
        
        if not a_texts or not q_texts:
            return []
            
        q_embeddings = rag.model.encode(q_texts, convert_to_numpy=True)
        a_embeddings = rag.model.encode(a_texts, convert_to_numpy=True)
        
        for i, q in enumerate(questions):
            best_answer = None
            best_score = 0.0
            best_method = "none"
            
            for j, a in enumerate(answers):
                score, method = self._calculate_link_score(q, a, q_embeddings[i], a_embeddings[j])
                
                if score > best_score:
                    best_score = score
                    best_answer = a
                    best_method = method
            
            # Threshold for accepting a link
            if best_answer and best_score > 0.65:
                links.append({
                    "question": q,
                    "answer": best_answer,
                    "confidence": round(best_score, 4),
                    "link_method": best_method
                })
        
        return links
    
    def _calculate_link_score(self, q: Dict, a: Dict, q_emb: np.ndarray, a_emb: np.ndarray) -> tuple:
        """Multi-factor scoring"""
        score = 0.0
        method = "semantic"
        
        # Rule 1: Answer must appear after or on same page as question
        if a['page'] < q['page']:
            return 0.0, "invalid_order"
            
        # Rule 2: Semantic similarity (Cosine)
        similarity = np.dot(q_emb, a_emb) / (np.linalg.norm(q_emb) * np.linalg.norm(a_emb))
        score += similarity * 0.6
        
        # Rule 3: Structural Proximity
        # Bonus if on same page
        if a['page'] == q['page']:
            score += 0.2
            method = "structural_bonus"
            
        # Rule 4: Explicit ID matching (e.g. Q1 -> A1)
        # Parse numbers from text
        q_num = self._extract_number(q['text'])
        a_num = self._extract_number(a['text'])
        
        if q_num and a_num and q_num == a_num:
            score += 0.4
            method = "explicit_id_match"
            
        # Rule 5: MCQ Option Matching
        # If Question has options (A)(B) and Answer says "Option A"
        if self._matches_mcq_option(q, a):
            score += 0.3
            method = "mcq_option_match"
            
        return min(score, 1.0), method

    def _extract_number(self, text: str) -> Optional[str]:
        """Extract leading number like '1.' or 'Q1'"""
        match = re.search(r'^(?:Q\s*|Question\s*)?(\d+)[\.:\)]', text, re.I)
        if match:
            return match.group(1)
        return None

    def _matches_mcq_option(self, q: Dict, a: Dict) -> bool:
        """Check if answer references an option present in question"""
        # Simple check: Does answer text start with a single letter that appears as option in Q?
        # Q: "(A) Apple (B) Banana"
        # A: "A" or "(A)" or "Option A"
        
        a_match = re.search(r'^(?:Option\s*)?\(?([A-D])\)?', a['text'], re.I)
        if a_match:
            opt = a_match.group(1).upper()
            # Check if Q contains this option indicator
            if f"({opt})" in q['text'] or f"{opt}." in q['text']:
                return True
        return False
