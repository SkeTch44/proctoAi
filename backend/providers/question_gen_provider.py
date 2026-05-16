import logging
from backend.utils.lazy_loader import LazyLoader
from backend.questions import QuestionGenerator

logger = logging.getLogger(__name__)

def _load_question_generator():
    """Inner loader for AI Question Generator."""
    logger.info("[QuestionGenProvider] Initializing AI Question Generator...")
    return QuestionGenerator()

def get_question_generator():
    """
    Get the QuestionGenerator instance.
    This component manages the RAG and LLM clients internally.
    """
    generator = LazyLoader.get("question_generator", _load_question_generator)
    
    # Simple check for required attributes
    if not hasattr(generator, 'pdf_parser'):
        logger.warning("[QuestionGenProvider] Generator instance invalid. Resetting.")
        LazyLoader.reset("question_generator")
        generator = LazyLoader.get("question_generator", _load_question_generator)
        
    return generator
