import logging
from backend.utils.lazy_loader import LazyLoader
from backend.utils.rag_engine import RAGEngine

logger = logging.getLogger(__name__)

def _load_rag():
    """Inner loader for RAG Engine."""
    logger.info("[RAGProvider] Initializing FAISS and Sentence Transformers...")
    return RAGEngine(store_path="backend/db/rag_store")

def get_rag_engine():
    """
    Get the RAG engine instance.
    Critically, RAGEngine has its own internally lazy-loaded model.
    """
    engine = LazyLoader.get("rag", _load_rag)
    
    # Fault-tolerance
    try:
        if hasattr(engine, 'get_stats') and 'error' in engine.get_stats():
            logger.warning("[RAGProvider] RAG engine reporting errors. Resetting.")
            LazyLoader.reset("rag")
            engine = LazyLoader.get("rag", _load_rag)
    except Exception as e:
        logger.error(f"[RAGProvider] RAG health check failed: {e}")
        LazyLoader.reset("rag")
        engine = LazyLoader.get("rag", _load_rag)
        
    return engine
