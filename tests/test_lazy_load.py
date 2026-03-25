import sys
import time
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LazyLoadTest")

def test_lazy_import():
    start_time = time.time()
    
    logger.info("Importing backend.app...")
    import backend.app
    app_time = time.time()
    logger.info(f"Imported backend.app in {app_time - start_time:.4f}s")
    
    logger.info("Importing backend.tasks...")
    import backend.tasks
    tasks_time = time.time()
    logger.info(f"Imported backend.tasks in {tasks_time - app_time:.4f}s")
    
    # Check if global variables are None
    if backend.app._question_generator is None:
        logger.info("✅ backend.app._question_generator is None (Lazy)")
    else:
        logger.error("❌ backend.app._question_generator is NOT None (Eager)")
        
    if backend.app._grading_engine is None:
        logger.info("✅ backend.app._grading_engine is None (Lazy)")
    else:
        logger.error("❌ backend.app._grading_engine is NOT None (Eager)")
        
    # Check tasks lazy vars (if accessible)
    # tasks.py doesn't expose them in __all__, but we can access via module
    if hasattr(backend.tasks, '_cheat_detector'):
        if backend.tasks._cheat_detector is None:
            logger.info("✅ backend.tasks._cheat_detector is None (Lazy)")
        else:
            logger.error("❌ backend.tasks._cheat_detector is NOT None (Eager)")

if __name__ == "__main__":
    test_lazy_import()
