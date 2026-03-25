import os
import sys
import time
import logging
from unittest.mock import MagicMock, patch

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("LazyTest")

def time_import(module_name):
    start = time.time()
    try:
        __import__(module_name)
        duration = time.time() - start
        logger.info(f"📦 Imported {module_name} in {duration:.4f}s")
    except ImportError:
        logger.warning(f"⚠️ Could not import {module_name}")
    except Exception as e:
        logger.error(f"❌ Error importing {module_name}: {e}")

def run_tests():
    logger.info("Starting Import Timing Tests...")
    
    # Time dependencies
    time_import('sentence_transformers')
    time_import('faiss')
    try:
        time_import('ultralytics')
    except: pass
    
    logger.info("Starting Class Initialization Tests...")

    # Test QuestionGenerator
    logger.info("Testing QuestionGenerator...")
    start_qg = time.time()
    from backend.engine.questions import QuestionGenerator
    logger.info(f"Imported backend.questions in {time.time() - start_qg:.4f}s")
    
    start_init = time.time()
    qg = QuestionGenerator()
    duration = time.time() - start_init
    
    if qg._rag_engine is not None:
        logger.error("❌ QuestionGenerator._rag_engine should be None")
        return False
    if qg._llm_client is not None:
        logger.error("❌ QuestionGenerator._llm_client should be None")
        return False
    logger.info(f"✅ QuestionGenerator instantiated in {duration:.4f}s")
    
    # Test GradingEngine
    logger.info("Testing GradingEngine...")
    start_ge = time.time()
    from backend.engine.grading import GradingEngine
    logger.info(f"Imported backend.grading in {time.time() - start_ge:.4f}s")
    
    start_init = time.time()
    ge = GradingEngine()
    duration = time.time() - start_init
    
    if ge._sim_model is not None:
        logger.error("❌ GradingEngine._sim_model should be None")
        return False
    logger.info(f"✅ GradingEngine instantiated in {duration:.4f}s")

    # Test CheatDetector
    logger.info("Testing CheatDetector...")
    start_cd = time.time()
    from backend.models.cheat_detector import CheatDetector
    logger.info(f"Imported backend.models.cheat_detector in {time.time() - start_cd:.4f}s")
    
    start_init = time.time()
    cd = CheatDetector()
    duration = time.time() - start_init
    
    if cd._yolo is not None:
        logger.error("❌ CheatDetector._yolo should be None")
        return False
    # Check internal attribute, DO NOT access property cd.gaze
    if cd._gaze is not None:
        logger.error("❌ CheatDetector._gaze should be None")
        return False
    logger.info(f"✅ CheatDetector instantiated in {duration:.4f}s")
    
    # Test RAGEngine
    logger.info("Testing RAGEngine...")
    start_rag = time.time()
    from backend.utils.rag_engine import RAGEngine
    logger.info(f"Imported backend.utils.rag_engine in {time.time() - start_rag:.4f}s")
    
    start_init = time.time()
    rag = RAGEngine()
    duration = time.time() - start_init
    
    if rag._model is not None:
        logger.error("❌ RAGEngine._model should be None")
        return False
    if rag._index is not None:
        logger.error("❌ RAGEngine._index should be None")
        return False
    logger.info(f"✅ RAGEngine instantiated in {duration:.4f}s")
    
    return True

if __name__ == "__main__":
    if run_tests():
        logger.info("🎉 All Lazy Loading Tests Passed!")
        sys.exit(0)
    else:
        logger.error("💥 Some tests failed.")
        sys.exit(1)
