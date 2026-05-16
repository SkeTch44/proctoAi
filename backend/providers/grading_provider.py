import logging
from backend.utils.lazy_loader import LazyLoader
from backend.grading import GradingEngine

logger = logging.getLogger(__name__)

def _load_grading_engine():
    """Inner loader for Grading Engine."""
    logger.info("[GradingProvider] Initializing Grading Engine...")
    return GradingEngine()

def get_grading_engine():
    """
    Get the GradingEngine instance.
    Used for automated answer evaluation.
    """
    return LazyLoader.get("grading_engine", _load_grading_engine)
