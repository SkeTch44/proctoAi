# backend/batch_processor.py

import os

import logging
from typing import List, Dict, Any
from datetime import datetime
from uuid import uuid4

from questions import QuestionGenerator
from enhanced_question import EnhancedQuestionGenerator
from db.database import DatabaseManager

logger = logging.getLogger(__name__)

class BatchProcessor:
    """
    BatchProcessor handles batch document uploads and question generation tasks.
    - Accepts multiple files
    - Parses each, stores content
    - Generates questions via AI or enhanced generator
    - Saves results and returns summary
    """

    def __init__(self, db_url: str = None):
        self.db = DatabaseManager(db_url or os.getenv("DATABASE_URL"))
        self.basic_gen = QuestionGenerator()
        self.enhanced_gen = EnhancedQuestionGenerator()

    def process_documents(self, user_id: int, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process a batch of uploaded documents.
        files: List of dicts with keys: 'filename', 'content' (raw text)
        Returns a summary with document IDs and statuses.
        """
        summary = {"processed": [], "errors": []}
        for f in files:
            filename = f.get("filename")
            content = f.get("content", "")
            try:
                if not content or len(content) < 50:
                    raise ValueError("Content too short or empty")

                # Store document
                doc_id = self.db.store_document(
                    user_id=user_id,
                    filename=filename,
                    original_content=content,
                    translated_content=None,
                    language_info={},
                    file_size=len(content)
                )

                # Build RAG index
                # (if using RAG engine)
                # rag_engine.add_document(doc_id, content)

                summary["processed"].append({
                    "filename": filename,
                    "document_id": doc_id,
                    "status": "stored"
                })
            except Exception as e:
                logger.error(f"Batch upload failed for {filename}: {e}")
                summary["errors"].append({"filename": filename, "error": str(e)})
        return summary

    def generate_batch_questions(
        self,
        user_id: int,
        document_ids: List[int],
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate questions for a batch of document IDs based on a config dict.
        config e.g.: {"mcq": {...}, "short_answer": {...}}
        Returns mapping doc_id -> questions list.
        """
        results = {"documents": {}, "errors": []}
        for doc_id in document_ids:
            try:
                # Fetch stored document
                doc = self.db.get_document(user_id, doc_id)
                if not doc:
                    raise ValueError("Document not found")

                content = doc["original_content"]
                # Choose enhanced or basic generator based on config
                if config.get("enhanced", False):
                    qs = self.enhanced_gen.generate_questions(content, config)
                else:
                    # Basic generator expects count & difficulty
                    count = config.get("count", 10)
                    difficulty = config.get("difficulty", "medium")
                    qs = self.basic_gen.generate_questions(content, count, difficulty)

                # Save questions to DB
                saved_ids = []
                for q in qs:
                    q_id = self.db.save_question(user_id, doc_id, q)
                    if q_id:
                        saved_ids.append(q_id)

                results["documents"][doc_id] = {
                    "filename": doc["filename"],
                    "question_count": len(saved_ids),
                    "question_ids": saved_ids
                }
            except Exception as e:
                logger.error(f"Question generation failed for doc {doc_id}: {e}")
                results["errors"].append({"document_id": doc_id, "error": str(e)})
        return results
