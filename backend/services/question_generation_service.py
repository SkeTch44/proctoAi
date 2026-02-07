"""
Question Generation Service

Unified service for all 3 question generation modes:
1. Pure AI Generation - Generate questions from topic
2. RAG + LLM - Generate from uploaded documents
3. PDF Scan - Extract existing questions from PDFs
"""

import os
import logging
import json
import tempfile
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import asdict

logger = logging.getLogger(__name__)

# Import backend components
from backend.utils.skill_compiler import get_skill_compiler, SkillPacket
from backend.llm_runner import LLMRunner
from backend.utils.pdf_extractor import MultiLayerPDFExtractor
from backend.utils.question_parser import QuestionParser
from backend.question_bank import QuestionBankManager, Question, QuestionType


class QuestionGenerationService:
    """
    Unified service for all question generation modes.
    
    Modes:
        1. generate_pure_ai() - AI generates questions from topic only
        2. generate_rag() - Upload doc → RAG extract → LLM generates
        3. scan_pdf() - Extract existing questions from PDF
    """
    
    def __init__(self, db_path: str = "exam_platform.db"):
        self.skill_compiler = get_skill_compiler()
        self.pdf_extractor = MultiLayerPDFExtractor()
        self.question_parser = QuestionParser()
        self.question_bank = QuestionBankManager(db_path)
        
        # Try to initialize RAG engine (optional)
        self.rag_engine = None
        try:
            from backend.utils.rag_engine import RAGEngine
            self.rag_engine = RAGEngine()
            logger.info("RAG engine initialized")
        except Exception as e:
            logger.warning(f"RAG engine not available: {e}")
    
    # ==================== MODE 1: PURE AI GENERATION ====================
    
    def generate_pure_ai(
        self,
        topic: str,
        count: int = 10,
        difficulty: str = "medium",
        question_types: List[str] = None,
        bank_id: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate questions entirely from AI without any source document.
        
        Args:
            topic: Subject/topic for questions
            count: Number of questions to generate
            difficulty: easy/medium/hard/expert
            question_types: List of types (mcq, short_answer, essay)
            bank_id: Optional question bank to add to
            user_id: User creating the questions
            
        Returns:
            Dict with 'success', 'questions', 'message'
        """
        logger.info(f"Pure AI generation: topic={topic}, count={count}, difficulty={difficulty}")
        
        if not question_types:
            question_types = ["mcq"]
        
        all_questions = []
        
        # Generate for each question type
        for q_type in question_types:
            # Determine count per type
            type_count = count // len(question_types)
            if q_type == question_types[-1]:
                type_count = count - len(all_questions)  # Remaining
            
            # Select appropriate skill
            skill_name = self._get_skill_for_type(q_type)
            
            try:
                # Compile skill
                packet = self.skill_compiler.compile_skill(skill_name, {
                    "topic": topic,
                    "count": type_count,
                    "difficulty": difficulty,
                    "context": f"Generate questions about {topic}. No specific document context provided."
                })
                
                # Execute LLM
                result = LLMRunner.execute(packet)
                
                if result:
                    # Normalize result
                    questions = self._normalize_llm_response(result, q_type, topic)
                    all_questions.extend(questions)
                    logger.info(f"Generated {len(questions)} {q_type} questions")
                else:
                    logger.warning(f"LLM returned no results for {q_type}")
                    
            except Exception as e:
                logger.error(f"Error generating {q_type} questions: {e}")
        
        # Save to question bank
        saved_count = 0
        if all_questions:
            saved_count = self._save_to_question_bank(all_questions, user_id, bank_id)
        
        return {
            'success': len(all_questions) > 0,
            'questions': all_questions,
            'count': len(all_questions),
            'saved_count': saved_count,
            'message': f"Generated {len(all_questions)} questions, saved {saved_count} to bank"
        }
    
    # ==================== MODE 2: RAG + LLM GENERATION ====================
    
    def generate_rag(
        self,
        file_path: str,
        topic: str = "Document Content",
        count: int = 10,
        difficulty: str = "medium",
        question_types: List[str] = None,
        bank_id: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate questions from uploaded document using RAG.
        
        Args:
            file_path: Path to uploaded PDF/DOCX
            topic: Topic name for categorization
            count: Number of questions
            difficulty: Difficulty level
            question_types: Types of questions to generate
            bank_id: Question bank to add to
            user_id: User ID
            
        Returns:
            Dict with 'success', 'questions', 'message'
        """
        logger.info(f"RAG generation: file={file_path}, topic={topic}, count={count}")
        
        if not question_types:
            question_types = ["mcq"]
        
        # Step 1: Extract text from document
        try:
            text_blocks = self.pdf_extractor.extract(file_path)
            if not text_blocks:
                return {
                    'success': False,
                    'questions': [],
                    'message': "Could not extract text from document"
                }
            
            # Combine text for context
            full_text = "\n".join([block.get('text', '') for block in text_blocks])
            logger.info(f"Extracted {len(full_text)} characters from document")
            
        except Exception as e:
            logger.error(f"Document extraction failed: {e}")
            return {
                'success': False,
                'questions': [],
                'message': f"Document extraction failed: {str(e)}"
            }
        
        # Step 2: Optional RAG indexing for retrieval
        context = full_text[:6000]  # Limit context size
        
        if self.rag_engine:
            try:
                # Add document to RAG
                self.rag_engine.add_document(full_text, metadata={"topic": topic, "file": file_path})
                
                # Retrieve relevant chunks for the topic
                retrieved = self.rag_engine.retrieve(topic, top_k=5)
                if retrieved:
                    context = "\n\n".join([chunk['text'] for chunk in retrieved])
                    logger.info(f"RAG retrieved {len(retrieved)} relevant chunks")
            except Exception as e:
                logger.warning(f"RAG retrieval failed, using full text: {e}")
        
        # Step 3: Generate questions using LLM
        all_questions = []
        
        for q_type in question_types:
            type_count = count // len(question_types)
            if q_type == question_types[-1]:
                type_count = count - len(all_questions)
            
            skill_name = self._get_skill_for_type(q_type)
            
            try:
                packet = self.skill_compiler.compile_skill(skill_name, {
                    "topic": topic,
                    "count": type_count,
                    "difficulty": difficulty,
                    "context": context
                })
                
                result = LLMRunner.execute(packet)
                
                if result:
                    questions = self._normalize_llm_response(result, q_type, topic)
                    all_questions.extend(questions)
                    
            except Exception as e:
                logger.error(f"Error generating {q_type} from RAG: {e}")
        
        # Step 4: Save to question bank
        saved_count = 0
        if all_questions:
            # Add source document metadata
            for q in all_questions:
                q['metadata'] = {'source_document': os.path.basename(file_path)}
            saved_count = self._save_to_question_bank(all_questions, user_id, bank_id)
        
        return {
            'success': len(all_questions) > 0,
            'questions': all_questions,
            'count': len(all_questions),
            'saved_count': saved_count,
            'document_chars': len(full_text),
            'message': f"Generated {len(all_questions)} questions from document"
        }
    
    # ==================== MODE 3: PDF SCAN / EXTRACTION ====================
    
    def scan_pdf(
        self,
        file_path: str,
        topic: str = "Extracted Questions",
        bank_id: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Scan an existing question PDF and extract questions.
        
        Args:
            file_path: Path to question PDF
            topic: Topic name for categorization
            bank_id: Question bank to add to
            user_id: User ID
            
        Returns:
            Dict with 'success', 'questions', 'message'
        """
        logger.info(f"PDF scan: file={file_path}, topic={topic}")
        
        # Step 1: Extract text from PDF
        try:
            text_blocks = self.pdf_extractor.extract(file_path)
            if not text_blocks:
                return {
                    'success': False,
                    'questions': [],
                    'message': "Could not extract text from PDF"
                }
                
            logger.info(f"Extracted {len(text_blocks)} text blocks from PDF")
            
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            return {
                'success': False,
                'questions': [],
                'message': f"PDF extraction failed: {str(e)}"
            }
        
        # Step 2: Parse questions from text
        try:
            parsed_questions = self.question_parser.parse(text_blocks)
            logger.info(f"Parsed {len(parsed_questions)} questions from PDF")
            
        except Exception as e:
            logger.error(f"Question parsing failed: {e}")
            return {
                'success': False,
                'questions': [],
                'message': f"Question parsing failed: {str(e)}"
            }
        
        # Step 3: Convert to question bank format
        all_questions = []
        for pq in parsed_questions:
            q = {
                'question_text': pq.question_text,
                'question_type': pq.question_type.value,
                'topic': topic,
                'points': pq.marks or 1,
                'difficulty': 'medium',  # Default, could be enhanced with AI classification
                'status': 'draft',
                'question_data': {
                    'options': pq.options,
                    'correct_answer': pq.correct_answer
                },
                'metadata': {
                    'source_document': os.path.basename(file_path),
                    'page_number': pq.page_number,
                    'extraction_confidence': pq.confidence
                }
            }
            all_questions.append(q)
        
        # Step 4: Save to question bank
        saved_count = 0
        if all_questions:
            saved_count = self._save_to_question_bank(all_questions, user_id, bank_id)
        
        return {
            'success': len(all_questions) > 0,
            'questions': all_questions,
            'count': len(all_questions),
            'saved_count': saved_count,
            'message': f"Extracted {len(all_questions)} questions from PDF"
        }
    
    # ==================== HELPER METHODS ====================
    
    def _get_skill_for_type(self, q_type: str) -> str:
        """Map question type to skill name"""
        mapping = {
            'mcq': 'mcq_generation',
            'short_answer': 'short_answer_generation',
            'essay': 'descriptive_generation',
            'true_false': 'mcq_generation',  # Use MCQ with 2 options
            'fill_blanks': 'short_answer_generation'
        }
        return mapping.get(q_type, 'mcq_generation')
    
    def _normalize_llm_response(self, result: Any, q_type: str, topic: str) -> List[Dict]:
        """Normalize LLM response to standard question format"""
        questions = []
        
        # Handle list or dict response
        if isinstance(result, list):
            raw_questions = result
        elif isinstance(result, dict) and 'questions' in result:
            raw_questions = result['questions']
        else:
            raw_questions = [result]
        
        for i, rq in enumerate(raw_questions):
            if not isinstance(rq, dict):
                continue
            
            q = {
                'question_text': rq.get('question', rq.get('question_text', '')),
                'question_type': q_type,
                'topic': topic,
                'difficulty': rq.get('difficulty', 'medium'),
                'points': rq.get('points', 1),
                'status': 'draft',
                'question_data': {}
            }
            
            # Handle MCQ options
            if q_type == 'mcq':
                options = rq.get('options', {})
                if isinstance(options, list):
                    options = {chr(65+i): opt for i, opt in enumerate(options)}
                q['question_data']['options'] = options
                q['question_data']['correct_answer'] = rq.get('answer', rq.get('correct_answer'))
            
            # Handle short answer
            elif q_type == 'short_answer':
                q['question_data']['expected_answer'] = rq.get('answer', rq.get('expected_answer', ''))
            
            if q['question_text']:
                questions.append(q)
        
        return questions
    
    def _save_to_question_bank(
        self, 
        questions: List[Dict], 
        user_id: Optional[int],
        bank_id: Optional[int]
    ) -> int:
        """Save questions to question bank"""
        saved_count = 0
        
        for q_data in questions:
            try:
                question = Question(
                    question_text=q_data.get('question_text', ''),
                    question_type=q_data.get('question_type', 'mcq'),
                    topic=q_data.get('topic', ''),
                    difficulty=q_data.get('difficulty', 'medium'),
                    points=q_data.get('points', 1),
                    question_data=q_data.get('question_data', {}),
                    status=q_data.get('status', 'draft'),
                    created_by=user_id
                )
                
                question_id = self.question_bank.create_question(question)
                
                if question_id:
                    saved_count += 1
                    
                    # Add to specific bank if provided
                    if bank_id:
                        self.question_bank.add_question_to_bank(bank_id, question_id, user_id)
                        
            except Exception as e:
                logger.error(f"Failed to save question: {e}")
        
        logger.info(f"Saved {saved_count}/{len(questions)} questions to bank")
        return saved_count


# Singleton instance
_service_instance = None

def get_question_generation_service() -> QuestionGenerationService:
    """Get singleton service instance"""
    global _service_instance
    if _service_instance is None:
        _service_instance = QuestionGenerationService()
    return _service_instance
