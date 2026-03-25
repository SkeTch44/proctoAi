import math
import logging
from typing import Dict, List, Any
from backend.config import Config

logger = logging.getLogger(__name__)

class UniversalQuestionEngine:
    """
    Step 4: Universal Batch Calculator & Orchestrator Logic
    """
    
    @staticmethod
    def calculate_work_units(request: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Step 2: Convert Request -> Work Units (Batches)
        Step 4: Universal Batch Calculator
        """
        work_units = []
        exam_id = request.get("exam_id")
        
        # Format breakdown: {"mcq": 40, ...}
        formats = request.get("format", {})
        
        for format_type, total_count in formats.items():
            rule = Config.FORMAT_RULES.get(format_type, {"batch": 1, "tokens": 512})
            batch_size = rule["batch"]
            
            # Calculate number of batches needed
            num_batches = math.ceil(total_count / batch_size)
            
            logger.info(f"Format: {format_type}, Total: {total_count}, Batch Size: {batch_size}, Batches Needed: {num_batches}")
            
            # Create work units
            for i in range(num_batches):
                # Calculate size for this specific batch (last one might be smaller)
                remaining = total_count - (i * batch_size)
                current_batch_size = min(batch_size, remaining)
                
                work_units.append({
                    "job_id": f"{exam_id}_{format_type}_{i}", # unique batch ID
                    "exam_id": exam_id,
                    "format_type": format_type,
                    "batch_index": i,
                    "batch_size": current_batch_size,
                    "total_batches": num_batches,
                    "status": "pending"
                })
                
        return work_units
