
import logging
import os
import shutil
from typing import Optional
from backend.utils.rag_engine import RAGEngine
from backend.db.database import DatabaseManager

logger = logging.getLogger(__name__)

class RAGManager:
    """
    Manages multiple RAG indices for PDF versioning.
    Wrapper around RAGEngine to handle different store paths.
    """
    
    def __init__(self, db: DatabaseManager, base_path: str = "backend/db/rag_store"):
        self.db = db
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)

    def get_engine(self, index_id: str) -> RAGEngine:
        """Get RAG engine for a specific index ID"""
        store_path = os.path.join(self.base_path, index_id)
        return RAGEngine(store_path=store_path)

    def create_versioned_index(self, pdf_id: str) -> Tuple[str, RAGEngine]:
        """
        Create a new versioned index for a PDF.
        Returns: (index_id, RAGEngine instance)
        """
        conn = self.db.get_connection()
        try:
            # Get latest version
            cursor = conn.execute(
                "SELECT MAX(version) FROM rag_indices WHERE pdf_id = ?",
                (pdf_id,)
            )
            result = cursor.fetchone()
            latest_version = result[0] if result and result[0] else 0
            new_version = latest_version + 1
            
            index_id = f"{pdf_id}_v{new_version}"
            store_path = os.path.join(self.base_path, index_id)
            
            # Register in DB
            conn.execute('''
                INSERT INTO rag_indices (index_id, pdf_id, version, index_path)
                VALUES (?, ?, ?, ?)
            ''', (index_id, pdf_id, new_version, store_path))
            conn.commit()
            
            logger.info(f"Created new RAG index: {index_id}")
            return index_id, RAGEngine(store_path=store_path)
            
        except Exception as e:
            logger.error(f"Failed to create versioned index: {e}")
            raise
        finally:
            conn.close()

    def delete_index(self, index_id: str):
        """Delete an index from disk and DB"""
        store_path = os.path.join(self.base_path, index_id)
        try:
            if os.path.exists(store_path):
                shutil.rmtree(store_path)
            
            conn = self.db.get_connection()
            conn.execute("DELETE FROM rag_indices WHERE index_id = ?", (index_id,))
            conn.commit()
            conn.close()
            logger.info(f"Deleted RAG index: {index_id}")
        except Exception as e:
            logger.error(f"Failed to delete index {index_id}: {e}")
