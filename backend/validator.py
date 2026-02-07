import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class Validator:
    """
    Phase 5: Validator
    Responsibility: Enforce Output Hygiene
    - Schema Validation
    - Constraint Checking (MCQ has 4 opts, etc.)
    - Deduplication (basic)
    """
    
    @staticmethod
    def validate_batch(generated_data: Any, expected_type: str, count: int) -> List[Dict]:
        """
        Validates the raw LLM output against rules.
        Returns a list of CLEAN, VALID questions.
        Drops invalid ones.
        """
        valid_questions = []
        
        # 1. Type Check: Must be list
        if not isinstance(generated_data, list):
            logger.error(f"Validator Rule 1 Failed: Expected list, got {type(generated_data)}")
            # Try to partial recover if it's a dict containing a list
            if isinstance(generated_data, dict) and 'questions' in generated_data:
                generated_data = generated_data['questions']
            else:
                return []
                
        # 2. Iterate and Validate
        for i, q in enumerate(generated_data):
            try:
                # Common checks
                if not isinstance(q, dict): continue
                if 'question' not in q or not q['question']: continue
                
                # Type Specific Checks
                if expected_type == 'mcq':
                    if not Validator._validate_mcq(q):
                        logger.warning(f"MCQ Validation Failed for item {i}")
                        continue
                
                elif expected_type == 'short_answer':
                    if 'sample_answer' not in q and 'expected_answer' not in q:
                        # Auto-fix common key mismatch if possible
                        continue
                        
                # Pass
                valid_questions.append(q)
                
            except Exception as e:
                logger.warning(f"Item {i} failed validation: {e}")
                
        # 3. Count Check (Optional strictness)
        if len(valid_questions) != count:
            logger.warning(f"Validator: Requested {count}, but got {len(valid_questions)} valid items.")
            
        return valid_questions

    @staticmethod
    def _validate_mcq(q: Dict) -> bool:
        # Check options
        opts = q.get('options')
        if not opts: return False
        
        # Must be dict {A:..., B:...} or List with 4 items
        if isinstance(opts, dict):
            if len(opts) != 4: return False
            if not all(k in opts for k in ['A','B','C','D']): return False
        elif isinstance(opts, list):
            if len(opts) != 4: return False
        else:
            return False
            
        # Check answer
        ans = q.get('answer', q.get('correct_answer'))
        if not ans: return False
        if isinstance(opts, dict) and ans not in ['A','B','C','D']: return False
        
        return True

    @staticmethod
    def validate_pdf_exam(links: List[Dict]) -> Dict:
        """
        Validate extracted PDF exam structure.
        
        Returns:
            {
                "valid": True/False,
                "errors": [...],
                "warnings": [...]
            }
        """
        errors = []
        warnings = []
        
        if not links:
            return {"valid": False, "errors": ["No extracted questions found"], "warnings": []}
            
        # Check 1: Low confidence warnings
        low_conf_count = sum(1 for l in links if l.get('confidence', 0) < 0.8)
        if low_conf_count > 0:
            warnings.append(f"{low_conf_count} pairs have low confidence (< 0.8)")
            
        # Check 2: Duplicate questions
        seen_questions = set()
        duplicates = 0
        for l in links:
            q_text = l['question'].get('text', '')
            q_sig = q_text[:50] # Check first 50 chars
            if q_sig in seen_questions:
                duplicates += 1
            seen_questions.add(q_sig)
            
        if duplicates > 0:
            warnings.append(f"Found {duplicates} potential duplicate questions")
            
        # Check 3: Check for empty answers
        empty_answers = sum(1 for l in links if not l['answer'].get('text', '').strip())
        if empty_answers > 0:
            errors.append(f"{empty_answers} questions have empty answers")
            
        # Check 4: MCQ specific validation heuristics
        for i, l in enumerate(links):
            q_conf = l['question'].get('confidence', 0)
            q_text = l['question'].get('text', '')
            q_type_hint = l['question'].get('type_hint', '')
            
            # If high confidence question but very short text, warn
            if q_conf > 0.8 and len(q_text) < 15:
                 warnings.append(f"Link {i} has short question text: '{q_text}'")
                 
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
