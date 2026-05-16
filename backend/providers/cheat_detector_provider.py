import logging
from backend.utils.lazy_loader import LazyLoader
from backend.models.cheat_detector import CheatDetector

logger = logging.getLogger(__name__)

def _load_cheat_detector():
    """Inner loader for Unified Cheat Detector."""
    logger.info("[CheatDetectorProvider] Loading YOLO and Gaze Models...")
    # Passing default empty config or any required parameters
    return CheatDetector()

def get_cheat_detector():
    """
    Get the heavy-weight CheatDetector instance.
    This component uses significant RAM/GPU (YOLO).
    """
    detector = LazyLoader.get("cheat_detector", _load_cheat_detector)
    
    # Simple check: Ensure yolo member exists
    if not hasattr(detector, 'yolo'):
        logger.warning("[CheatDetectorProvider] Detector has no YOLODetector. Resetting.")
        LazyLoader.reset("cheat_detector")
        detector = LazyLoader.get("cheat_detector", _load_cheat_detector)
        
    return detector
