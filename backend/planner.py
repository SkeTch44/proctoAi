import uuid
import math
import logging
import json
from datetime import datetime
from typing import Dict, List, Any
from backend.config import Config

logger = logging.getLogger(__name__)

class ExamBlueprint:
    """Immutable blueprint for an exam generation run."""
    def __init__(self, exam_id: str, topic: str, difficulty: str, batches: List[Dict]):
        self.exam_id = exam_id
        self.topic = topic
        self.difficulty = difficulty
        self.batches = batches # List of batch configs
        self.created_at = datetime.utcnow().isoformat()

    def to_dict(self):
        return {
            "exam_id": self.exam_id,
            "topic": self.topic,
            "difficulty": self.difficulty,
            "batches": self.batches,
            "created_at": self.created_at,
            "total_questions": sum(b['count'] for b in self.batches)
        }

class Planner:
    """
    Phase 1: Planner
    Responsibility: Convert User Request -> Strict Execution Blueprint
    - Deterministic UUIDs
    - Strict Batch Sizing
    - No LLM calls
    """
    
    @staticmethod
    def create_blueprint(request_data: Dict[str, Any], user_id: str) -> ExamBlueprint:
        try:
            # 1. Input Validation
            topic = request_data.get('topic', 'General')
            difficulty = request_data.get('difficulty', 'medium')
            # support legacy 'total_questions' + default distribution OR specific breakdown
            total_questions = request_data.get('total_questions', 10) # default fallback
            
            # Format breakdown: {"mcq": 10, "short_answer": 5}
            # If not provided, assume all MCQ for legacy compatibility or split? 
            # Let's default to all MCQ if not specified to keep it simple, or use a default mix.
            formats = request_data.get('format', {'mcq': total_questions})
            
            # [FIX] exam_id MUST be provided by API (prevents split-brain bug)
            exam_id = request_data.get('exam_id')
            if not exam_id:
                exam_id = f"exam_{uuid.uuid4().hex[:8]}"
                logger.warning(f"[PLANNER] No exam_id provided, generated: {exam_id}")
            else:
                logger.info(f"[PLANNER] Using provided exam_id: {exam_id}")
            
            batches = []
            
            # 2. Batch Calculation
            for fmt, count in formats.items():
                rule = Config.FORMAT_RULES.get(fmt, {"batch": 5}) # Safe default
                max_batch_size = rule['batch']
                
                num_batches = math.ceil(count / max_batch_size)
                
                for i in range(num_batches):
                    # Deterministic Batch ID
                    batch_id = f"{exam_id}_{fmt}_{i}"
                    
                    # Calculate count for this batch
                    remaining = count - (i * max_batch_size)
                    batch_count = min(max_batch_size, remaining)
                    
                    batches.append({
                        "batch_id": batch_id,
                        "exam_id": exam_id,
                        "type": fmt,
                        "count": batch_count,
                        "difficulty": difficulty,
                        "topic": topic,
                        "content": request_data.get('content', ''),  # ← ADD for worker
                        "admin_id": user_id,  # ← ADD for worker
                        "status": "pending",
                        "index": i,
                        "total_batches": num_batches,
                        "user_id": user_id
                    })
            
            logger.info(f"Planned {len(batches)} batches for Exam {exam_id}")
            return ExamBlueprint(exam_id, topic, difficulty, batches)

        except Exception as e:
            logger.error(f"Planning failed: {e}")
            raise ValueError(f"Planning failed: {str(e)}")
