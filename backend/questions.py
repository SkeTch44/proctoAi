import os 
import json
import re
import logging
import uuid
from typing import List, Dict, Optional
import google.generativeai as genai
from datetime import datetime
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.utils.rag_engine import RAGEngine
from backend.utils.pdf_parser import PDFParser
from backend.utils.docx_parser import DOCXParser
from backend.utils.llm_client import LLMFactory


logger = logging.getLogger(__name__)

class QuestionGenerator:
    """AI-Powered question generation system using Gemini with RAG grounding"""
    
    def __init__(self, rag_store_path: str = "backend/db/rag_strore"):
        """Initialize Question Generator with RAG support"""
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model = None
        self.fallback_enabled = True
        
        # Initialize RAG engine
        try:
            self.rag_engine = RAGEngine(store_path=rag_store_path)
            logger.info("RAG engine initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize RAG engine: {e}")
            self.rag_engine = None
        
        # Initialize parsers
        self.pdf_parser = PDFParser(chunk_size=500, overlap=50)
        self.docx_parser = DOCXParser(chunk_size=500, overlap=50)
        
        # Initialize LLM Client via Factory
        self.llm_client = LLMFactory.create_client()
        if self.llm_client:
            logger.info(f"QuestionGenerator initialized with {self.llm_client.__class__.__name__}")
        else:
            logger.warning("No LLM client available. Questions will be generated using rule-based fallback only.")
    
    def process_document(self, file_path: str, doc_id: Optional[str] = None) -> Optional[str]:
        """
        Process a document (PDF/DOCX) and add to RAG store
        
        Args:
            file_path: Path to document
            doc_id: Optional document ID (auto-generated if not provided)
            
        Returns:
            Document ID if successful, None otherwise
        """
        if not self.rag_engine:
            logger.error("RAG engine not available")
            return None
        
        # Generate doc_id if not provided
        if not doc_id:
            doc_id = f"doc_{uuid.uuid4().hex[:8]}"
        
        # Determine file type and parse
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.pdf':
            chunks = self.pdf_parser.extract_text_with_chunking(file_path)
            metadata = self.pdf_parser.extract_metadata(file_path)
        elif file_ext in ['.docx', '.doc']:
            chunks = self.docx_parser.extract_text_with_chunking(file_path)
            metadata = self.docx_parser.extract_metadata(file_path)
        else:
            logger.error(f"Unsupported file type: {file_ext}")
            return None
        
        if not chunks:
            logger.error(f"No chunks extracted from {file_path}")
            return None
        
        # Add to RAG store
        num_added = self.rag_engine.add_document(doc_id, chunks, metadata)
        
        if num_added > 0:
            logger.info(f"Successfully processed document {doc_id} with {num_added} chunks")
            return doc_id
        else:
            logger.error(f"Failed to add document {doc_id} to RAG store")
            return None
    
    def generate_questions(self, content: str, num_questions: int = 10,
                          difficulty: str = "medium", topic: str = "",
                          use_rag: bool = True) -> List[Dict]:
        """
        Generate questions from content using AI with RAG grounding
        
        Args:
            content: Text content or query for RAG retrieval
            num_questions: Number of questions to generate
            difficulty: Difficulty level (easy, medium, hard, expert)
            topic: Optional topic for the questions
            use_rag: Whether to use RAG retrieval
            
        Returns:
            List of question dictionaries with metadata
        """
        if not content or len(content.strip()) < 10:
            logger.error("Content too short for question generation")
            return []
        
        try:
            # Use RAG if enabled and available
            context = content
            retrieved_chunks = []
            
            if use_rag and self.rag_engine and self.rag_engine.index.ntotal > 0:
                logger.info(f"Retrieving relevant chunks for: '{content[:50]}...'")
                retrieved_chunks = self.rag_engine.search(content, k=5)
                
                if retrieved_chunks:
                    # Combine retrieved chunks as context
                    context = "\n\n".join([chunk['text'] for chunk in retrieved_chunks])
                    logger.info(f"Using {len(retrieved_chunks)} retrieved chunks as context")
                else:
                    logger.warning("No chunks retrieved, using original content")
            
            # Generate questions with AI
            if self.llm_client:
                return self._generate_ai_questions(context, num_questions, difficulty, 
                                                   topic, retrieved_chunks)
            elif self.fallback_enabled:
                logger.warning("AI model not available, using fallback")
                return self._generate_fallback_questions(context, num_questions, difficulty)
            else:
                logger.error("No question generation method available")
                return []
                
        except Exception as e:
            logger.error(f"Failed to generate questions: {e}")
            if self.fallback_enabled:
                return self._generate_fallback_questions(content, num_questions, difficulty)
            return []
    
    def _generate_ai_questions(self, content: str, count: int, difficulty: str,
                              topic: str, retrieved_chunks: List[Dict]) -> List[Dict]:
        """Generate questions using Gemini AI model with improved prompts"""
        
        # Create grounding metadata
        grounding_info = ""
        chunk_ids = []
        if retrieved_chunks:
            grounding_info = "\n\nSOURCE CHUNKS (for grounding):\n"
            for i, chunk in enumerate(retrieved_chunks, 1):
                grounding_info += f"\n[Chunk {i} - ID: {chunk['chunk_id']}]\n{chunk['text'][:200]}...\n"
                chunk_ids.append(chunk['chunk_id'])
        
        prompt = self._create_improved_prompt(content, count, difficulty, topic, grounding_info)
        
        try:
            # Use specific LLM client
            response = self.llm_client.generate_content(prompt)
            
            if not response or not hasattr(response, 'text') or not response.text:
                raise Exception("Empty response from AI model")
            
            # Parse JSON response
            question_data = self._parse_ai_response(response.text)
            
            if not question_data or 'questions' not in question_data:
                raise Exception("Invalid response format from AI model")
            
            questions = question_data['questions']
            
            # Validate and enhance with metadata
            validated_questions = []
            for i, question in enumerate(questions[:count]):
                validated_q = self._validate_and_enhance_question(
                    question, i + 1, chunk_ids, difficulty, topic
                )
                if validated_q:
                    validated_questions.append(validated_q)
            
            logger.info(f"Generated {len(validated_questions)} AI questions with metadata")
            return validated_questions
            
        except Exception as e:
            logger.error(f"AI question generation error: {e}")
            raise
    
    def _create_improved_prompt(self, content: str, count: int, difficulty: str,
                               topic: str, grounding_info: str) -> str:
        """Create improved prompt with strict grounding and metadata requirements"""
        
        topic_instruction = f"Focus on the topic: {topic}" if topic else ""
        
        prompt = f"""You are an expert exam question generator. Generate EXACTLY {count} high-quality exam questions based STRICTLY on the provided content.

{topic_instruction}

CONTENT TO ANALYZE:
{content[:3000]}

{grounding_info}

CRITICAL REQUIREMENTS:
1. Questions MUST be directly answerable from the provided content - NO hallucinations
2. Generate a mix: 60% MCQ, 25% Short Answer, 15% Essay/Case Study
3. Difficulty level: {difficulty}
4. For MCQ: Provide exactly 4 options (A, B, C, D) with ONE correct answer
5. Include detailed explanations citing the source content
6. Add appropriate metadata for each question

DIFFICULTY GUIDELINES:
- easy: Direct recall, basic comprehension
- medium: Application, comparison, explanation
- hard: Analysis, synthesis, evaluation
- expert: Complex problem-solving, critical analysis

BLOOM'S TAXONOMY LEVELS:
- remember: Recall facts
- understand: Explain concepts
- apply: Use knowledge in new situations
- analyze: Break down and examine
- evaluate: Make judgments
- create: Produce new work

Return ONLY valid JSON in this EXACT format:
{{
  "questions": [
    {{
      "id": "q_1",
      "type": "mcq",
      "question": "Clear, specific question text?",
      "options": ["A) First option", "B) Second option", "C) Third option", "D) Fourth option"],
      "correct_answer": "A",
      "explanation": "Detailed explanation citing source content",
      "difficulty": "{difficulty}",
      "points": 1,
      "topic": "Specific topic from content",
      "subtopic": "More specific subtopic",
      "taxonomy": "apply"
    }},
    {{
      "id": "q_2",
      "type": "short_answer",
      "question": "Question requiring brief explanation?",
      "sample_answer": "Expected answer with key points",
      "explanation": "Grading criteria and key concepts",
      "difficulty": "{difficulty}",
      "points": 2,
      "topic": "Topic area",
      "subtopic": "Subtopic",
      "taxonomy": "understand"
    }},
    {{
      "id": "q_3",
      "type": "essay",
      "question": "Question requiring detailed analysis?",
      "sample_answer": "Comprehensive expected response",
      "explanation": "Evaluation criteria",
      "difficulty": "{difficulty}",
      "points": 5,
      "topic": "Topic area",
      "subtopic": "Subtopic",
      "taxonomy": "analyze"
    }}
  ]
}}

IMPORTANT: Return ONLY the JSON object, no markdown formatting, no additional text."""
        
        return prompt
    
    def _parse_ai_response(self, response_text: str) -> Dict:
        """Parse AI response and extract JSON"""
        cleaned_text = response_text.strip()
        
        # Remove markdown code blocks if present
        cleaned_text = re.sub(r'^```json\s*', '', cleaned_text)
        cleaned_text = re.sub(r'^```\s*', '', cleaned_text)
        cleaned_text = re.sub(r'\s*```$', '', cleaned_text)
        
        try:
            return json.loads(cleaned_text)
        except json.JSONDecodeError:
            # Try to find JSON object within text
            json_match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    pass
            
            raise Exception(f"Could not parse JSON from AI response: {cleaned_text[:200]}...")
    
    def _validate_and_enhance_question(self, question: Dict, index: int,
                                      chunk_ids: List[str], difficulty: str,
                                      topic: str) -> Optional[Dict]:
        """Validate and enhance question with metadata"""
        
        try:
            # Required fields
            if not question.get('question') or not question.get('type'):
                logger.warning(f"Question {index} missing required fields")
                return None
            
            # Build enhanced question
            enhanced_q = {
                'id': question.get('id', f"q_{uuid.uuid4().hex[:8]}"),
                'type': question.get('type', 'mcq').lower(),
                'question': question['question'].strip(),
                'difficulty': question.get('difficulty', difficulty).lower(),
                'points': int(question.get('points', 1)),
                'topic': question.get('topic', topic or 'General').strip(),
                'subtopic': question.get('subtopic', '').strip(),
                'taxonomy': question.get('taxonomy', 'remember').lower(),
                'explanation': question.get('explanation', '').strip(),
                'created_at': datetime.now().isoformat(),
                'grounding': {
                    'chunk_ids': chunk_ids,
                    'confidence_score': 0.9  # Can be enhanced with actual scoring
                }
            }
            
            # Type-specific validation
            if enhanced_q['type'] == 'mcq':
                options = question.get('options', [])
                correct_answer = question.get('correct_answer', '').strip().upper()
                
                if len(options) != 4:
                    logger.warning(f"Question {index}: MCQ must have exactly 4 options")
                    return None
                
                if not re.match(r'^[A-D]$', correct_answer):
                    logger.warning(f"Question {index}: Invalid correct answer '{correct_answer}'")
                    return None
                
                enhanced_q['options'] = [opt.strip() for opt in options]
                enhanced_q['correct_answer'] = correct_answer
                
            elif enhanced_q['type'] in ['short_answer', 'essay', 'case_study']:
                sample_answer = question.get('sample_answer', '').strip()
                if not sample_answer:
                    logger.warning(f"Question {index}: Missing sample answer")
                    return None
                enhanced_q['sample_answer'] = sample_answer
            
            else:
                logger.warning(f"Question {index}: Unsupported type '{enhanced_q['type']}'")
                return None
            
            return enhanced_q
            
        except Exception as e:
            logger.error(f"Question validation failed for question {index}: {e}")
            return None
    
    def _generate_fallback_questions(self, content: str, count: int, difficulty: str) -> List[Dict]:
        """Generate basic fallback questions when AI is unavailable"""
        logger.info(f"Generating {count} fallback questions")
        
        questions = []
        sentences = self._extract_meaningful_sentences(content)
        
        if not sentences:
            logger.warning("No meaningful sentences found for fallback generation")
            return []
        
        # Generate simple MCQ questions
        for i in range(min(count, len(sentences))):
            sentence = sentences[i]
            words = sentence.split()
            target_word = max(words, key=len) if words else "concept"
            
            question = {
                'id': f"fallback_q_{i+1}",
                'type': 'mcq',
                'question': f"According to the content, what is mentioned about '{target_word.lower()}'?",
                'options': [
                    f"A) {sentence[:60]}...",
                    "B) Alternative interpretation",
                    "C) Different concept",
                    "D) Unrelated information"
                ],
                'correct_answer': 'A',
                'explanation': f"The content specifically mentions: {sentence}",
                'difficulty': difficulty,
                'points': 1,
                'topic': 'Content Analysis',
                'subtopic': '',
                'taxonomy': 'remember',
                'created_at': datetime.now().isoformat(),
                'grounding': {'chunk_ids': [], 'confidence_score': 0.5}
            }
            questions.append(question)
        
        return questions
    
    def _extract_meaningful_sentences(self, content: str) -> List[str]:
        """Extract meaningful sentences from content"""
        sentences = re.split(r'[.!?]+', content)
        meaningful = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            # Filter: length > 30 chars, > 5 words, contains letters
            if (len(sentence) > 30 and 
                len(sentence.split()) > 5 and 
                any(c.isalpha() for c in sentence)):
                meaningful.append(sentence)
        
        return meaningful[:20]
    
    def get_rag_stats(self) -> Dict:
        """Get RAG engine statistics"""
        if self.rag_engine:
            return self.rag_engine.get_stats()
        return {'error': 'RAG engine not available'}