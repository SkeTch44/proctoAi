
import logging
import os
import json
from typing import Dict, Any

from backend.utils.pdf_extractor import MultiLayerPDFExtractor
from backend.utils.pdf_noise_filter import PDFNoiseFilter
from backend.utils.semantic_chunker import SemanticChunker
from backend.utils.pdf_classifier import PDFChunkClassifier
from backend.utils.rag_manager import RAGManager
from backend.utils.qa_linker import QALinker
from backend.validation.validator import Validator
from backend.utils.redis_manager import redis_manager
from backend.db.database import DatabaseManager

logger = logging.getLogger(__name__)

class PDFPipelineOrchestrator:
    """
    Orchestrates the 7-phase PDF-to-Exam pipeline.
    Connects to Redis for real-time progress updates.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.extractor = MultiLayerPDFExtractor(use_ocr=True)
        self.noise_filter = PDFNoiseFilter()
        self.chunker = SemanticChunker()
        self.classifier = PDFChunkClassifier() # Uses Ollama
        self.rag_manager = RAGManager(db_manager)
        self.linker = QALinker()
        
    def process_exam(self, job_id: str, pdf_path: str, exam_id: str) -> Dict[str, Any]:
        """
        Run the full pipeline.
        
        Args:
            job_id: Celery/Redis Job ID for progress tracking
            pdf_path: Local path to PDF
            exam_id: DB ID of the exam
            
        Returns:
            Review Data Dict {
                "links": [...],
                "validation": {...},
                "stats": {...}
            }
        """
        try:
            # Step 1: Initialization (0%)
            redis_manager.update_progress(job_id, current=0, status="Extracting text...")
            logger.info(f"Starting pipeline for exam {exam_id}")
            
            # Step 2: Extraction (10%)
            raw_blocks = self.extractor.extract(pdf_path)
            redis_manager.update_progress(job_id, current=20, status="Filtering noise...")
            logger.info(f"Extracted {len(raw_blocks)} raw blocks")
            
            # Step 3: Noise Filtering (30%)
            clean_blocks = self.noise_filter.filter_blocks(raw_blocks)
            redis_manager.update_progress(job_id, current=30, status="Structuring chunks...")
            logger.info(f"Filtered to {len(clean_blocks)} clean blocks")
            
            # Step 4: Semantic Chunking (40%)
            chunks = self.chunker.chunk(clean_blocks)
            redis_manager.update_progress(job_id, current=40, status="Indexing RAG...")
            logger.info(f"Created {len(chunks)} semantic chunks")
            
            # Step 5: RAG Indexing (50%)
            # Create versioned index
            index_id, rag_engine = self.rag_manager.create_versioned_index(f"exam_{exam_id}")
            rag_engine.add_chunks(f"exam_{exam_id}", chunks)
            redis_manager.update_progress(job_id, current=50, status="Classifying content (AI)...")
            logger.info(f"Indexed chunks into {index_id}")
            
            # Step 6: Classification (70%)
            # classify each chunk (This is the slow part -> call LLM)
            classified_chunks = []
            total = len(chunks)
            for i, chunk in enumerate(chunks):
                # Update progress within this phase
                if i % 5 == 0:
                    prog = 50 + int((i/total) * 20)
                    redis_manager.update_progress(job_id, current=prog)
                    
                cls_result = self.classifier.classify(chunk['text'])
                chunk['type'] = cls_result['type']
                chunk['confidence'] = cls_result['confidence']
                classified_chunks.append(chunk)
            
            redis_manager.update_progress(job_id, current=75, status="Linking Questions & Answers...")
            
            # Separate Qs and As
            questions = [c for c in classified_chunks if c['type'] == 'QUESTION']
            answers = [c for c in classified_chunks if c['type'] == 'ANSWER' or c['type'] == 'EXPLANATION' or c['type'] == 'OPTION']
            
            logger.info(f"Classified {len(questions)} Questions and {len(answers)} Answer candidates")
            
            # Step 7: Linking (90%)
            # Pass RAG engine for semantic comparison
            links = self.linker.link_questions_answers(questions, answers, rag_engine)
            redis_manager.update_progress(job_id, current=90, status="Validating structure...")
            logger.info(f"Formed {len(links)} Q-A links")
            
            # Step 8: Validation (95%)
            validation = Validator.validate_pdf_exam(links)
            
            result = {
                "exam_id": exam_id,
                "pdf_path": pdf_path,
                "index_id": index_id,
                "stats": {
                    "raw_blocks": len(raw_blocks),
                    "chunks": len(chunks),
                    "questions_found": len(questions),
                    "links_found": len(links)
                },
                "links": links,
                "validation": validation,
                "status": "ready_for_review"
            }
            
            redis_manager.update_progress(job_id, current=100, status="Completed")
            return result
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            redis_manager.set_job_failed(job_id, str(e))
            raise
