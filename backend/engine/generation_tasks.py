import os
import logging
from backend.celery_app import celery

# Configure logger
logger = logging.getLogger(__name__)

# Lazy loading components
_qn_service = None

def get_question_generation_service():
    global _qn_service
    if _qn_service is None:
        logger.info("Lazy loading QuestionGenerationService in worker...")
        from backend.services.question_generation_service import get_question_generation_service
        _qn_service = get_question_generation_service()
    return _qn_service

@celery.task(bind=True)
def generate_batch_task(self, params):
    """
    Async task to generate questions using QuestionGenerationService.
    Target for /api/generate_questions_universal
    """
    job_id = self.request.id
    logger.info(f"Starting batch generation job {job_id}")
    
    try:
        # Update status to processing
        self.update_state(state='PROCESSING', meta={'current': 0, 'total': params.get('count', 10)})
        
        # Get service
        service = get_question_generation_service()
        
        # Determine mode based on params
        topic = params.get('subject') or params.get('topic') or "General"
        count = params.get('total_questions') or params.get('count') or 10
        formats = params.get('format') or {'mcq': count}
        types = list(formats.keys())
        difficulty = params.get('difficulty', 'medium')
        
        # Call service (Synchronous for now, but wrapped in async task)
        # We use generate_pure_ai as the primary engine for now
        result = service.generate_pure_ai(
            topic=topic,
            count=count,
            difficulty=difficulty,
            question_types=types
        )
        
        if result.get('success'):
            return {
                'status': 'completed', 
                'questions': result.get('questions'), 
                'count': len(result.get('questions'))
            }
        else:
            error_msg = result.get('message', 'Generation failed')
            logger.error(f"Generation failed: {error_msg}")
            return {
                'status': 'failed',
                'message': error_msg,
                'questions': [],
                'count': 0
            }
            
    except Exception as e:
        logger.error(f"Generation task failed: {e}")
        # Return failure dict instead of raising to avoid Celery serialization issues
        return {
            'status': 'failed',
            'message': str(e),
            'questions': [],
            'count': 0
        }
