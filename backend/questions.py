import os 
import json
import re
import logging
import uuid
from typing import List, Dict, Optional

from datetime import datetime
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.utils.rag_engine import RAGEngine
from backend.utils.pdf_parser import PDFParser
from backend.utils.docx_parser import DOCXParser
from backend.utils.llm_client import LLMFactory


logger = logging.getLogger(__name__)

class QuestionGenerator:
<<<<<<< HEAD
    """ MAIN AI - Powered question generation system using gemini"""
    def __init__(self):
=======
    """AI-Powered question generation system using Gemini with RAG grounding"""
    
    def __init__(self, rag_store_path: str = "backend/db/rag_strore"):
        """Initialize Question Generator with RAG support"""
        self.api_key = os.getenv("GEMINI_API_KEY")
>>>>>>> rohan
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

<<<<<<< HEAD
Important: Return ONLY the JSON object, no additional text or formatting.
"""

                    return prompt
                def _parse_ai_response(self,response_text: str) -> Dict:
                    """Parse AI response and extract JSON"""
                    # clean the response text 

                    cleaned_text = response_text.strip()
                    # remove any markdown formatting
                    cleaned_text = re.sub(r"^'''[\s]*$", '', cleaned_text)
                                                                # try to find Json object
                    try:
                                                                    # first trying  the parsing the entire response
                                                                    return json.loads(cleaned_text)
                    except json.JSONDecodeError:
                                                                    # if that fails, try to find the JSON object within the text
                                                                    json_match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)
                                                                    if json_match:
                                                                        try:
                                                                         return json.loads(json_match.group(0))
                                                                        except json.JSONDecodeError:
                                                                            pass 
                                                                    # if all else fails, try to extract questions array
                                                                    question_match = re.search(r'"questions":\s*(\[[^\]]*\])', cleaned_text)
                                                                    if question_match:
                                                                        try:
                                                                         question_json = f'{{"questions": {question_match.group(1)}}}'
                                                                         return json.loads(question_json)
                                                                        except json.JSONDecodeError:
                                                                         pass
                                                                    raise Exception(f"Could not parse questions from AI response: {cleaned_text[:200]}...")
                                                                    def _validate_and_clean_question(self, question: Dict, index: int) -> Optional[Dict]:
                                                                        """Validate and clean generated question"""
                                                               

                                                                    try:
                                                                        question_id = f"q_{index}"
                                                                    # Required fields
                                                                        if not question.get('question') or not question.get('type'):
                                                                            logger.warning(f"Question {question_id} missing required fields")
                                                                            return None

                                                                        # clean the question 
                                                                            cleaned_question = {'id': question_id, 'type':
                                                                                                question.get('type','mcq').lower(),'question':
                                                                                                question['question'].strip(),'difficulty':
                                                                                                question.get('difficulty', 'medium').lower(),'points':
                                                                                                int(question.get('points', 1)),
                                                                                            'topic': question.get('topic', 'General').strip(),'bloom_level': question.get('bloom_level', 'knowledge').lower(),'explanation':question.get('explanation', '').strip()}

                                                                                        #    type - specific validation and cleaning
                                                                            if cleaned_question['type'] == 'mcq':
                                                                             options = question.get('options',[])
                                                                            correct_answer = question.get('correct_answer','').strip().upper()
                                                                            if len(options)!=4:
                                                                             logger.warning(f"Question {question_id} MCQ options must have exactly 4 choices")
                                                                            return None 
                                                                            if not re.match(r'^[A-D]$', correct_answer):
                                                                                                logger.warning(f"Question {question_id} invalid correct answer option: {correct_answer}")
                                                                                                return None
                                                                                                cleaned_question['options'] = [opt.strip() for opt in options]
                                                                                                cleaned_question['correct_answer'] = correct_answer

                                                                            elif cleaned_question['type'] in ['short_answer','essay']: sample_answer = question.get('sample_answer','').strip()
                                                                        if not sample_answer:
                                                                             logger.warning(f"question {question_id} missing sample answer")

                                                                             return None
                                                                             cleaned_question['sample_answer'] = sample_answer
                                                                        else:
                                                                            logger.warning(f"Question {question_id} has unsupported type: {cleaned_question['type']}")
                                                                            return None
                                                                            return cleaned_question
                                                                    except Exception as e:
                                                                                    logger.error(f"Question validation failed for question {question_id}: {e}")
                                                                                    return None

                                                                    def _generate_fallback_question(self, content: str, num_questions: int, difficulty: str) -> List[Dict]:
                                                                           """Generate basic Questions when Ai is not Available"""
                                                                           logger.info(f"Generating{count} fallback questions")
                                                                           questions = []
                                                                           sentences = self._extract_meaningful_sentences(content)
                                                                           if not sentences:
                                                                                  logger.warning("No meaningful found for fallback generation")
                                                                                  return []
                                                                           
                                                                           #genrates different types of questions 
                                                                           mcq_count = max(1, int(count * 0.6)) # 60% mcq
                                                                           short_count =  max(1,count(int(count * 0.25))) # 25% short answer
                                                                           essay_count = max(1, count - mcq_count - short_count) # Remaining for essay

                                                                        #    Generate MCQ questions
                                                                           for i in range(mcq_count):
                                                                               if i < len(sentences):
                                                                                   mcq = self._create_mcq_question(sentences[i], difficulty)
                                                                                   questions.append(mcq)

                                                                        #    Generate short answer type
                                                                           for i in range(short_count):
                                                                               if i < len(sentences):
                                                                                   short_q = self._create_short_answer_question(sentences[i], difficulty)
                                                                                   questions.append(short_q)

                                                                        #    Generate essay type
                                                                           for i in range(essay_count):
                                                                               if i < len(sentences):
                                                                                   essay_q = self._create_essay_question(sentences[i], difficulty)
                                                                                   questions.append(essay_q)

                                                                    def _extract_meaningful_sentences(self, content: str) -> List[str]:
                                                                       """Extract meaningful sentences from the content for the fallback generation."""
                                                                       # Implement your sentence extraction logic here
                                                                       sentences = re.split(r'[.!?]', content)
                                                                       #     filter meaningful sentences
                                                                    meaningful_sentences =[]
                                                                    for sentence in sentences:
                                                                     sentence = sentence.strip()
                                                                    #  skip short or meaningless sentences
                                                                     if len(sentence) > 30 and len(sentence.split()) > 5 and not sentence.lower().startswith(('the', 'a', 'an', 'this', 'that')) and any(c.isalpha() for c in sentence):
                                                                       meaningful_sentences.append(sentence)
                                                                    return meaningful_sentences[:20]  # limit to top 20 sentences
                                                                    def _create_fallback_mcq(self,sentences:str)->dict:
                                                                          """Create a fallback MCQ from a sentences"""
                                                                          words = sentences.split()
                                                                          #find a good word to ask  about (longer words are usally meaningful)
                                                                          target_words = max(words, key=len) if words else "concept"

                                                                        # create a simple MCQ
                                                                    question_text = f"According to the content, what is mentioned about '{target_words.lower()}'?" 
                                                                    return {
                                                                        "id": question_id,
                                                                        "type": "mcq",
                                                                        "question": question_text,
                                                                        "options": [
                                                                              f"A) {sentences[:50]}...",
                                                                              f"B) Alternative interpretation",
                                                                              f"C) Different concept",
                                                                              f"D) Unrelated information"
                                                                        ],
                                                                        'correct_answer': 'A',
                                                                        'explanation':f"The content specifically mentionns : {sentences}",
                                                                        'difficulty': 'difficulty',
                                                                        'points': 1,
                                                                        'topic': 'current Analysis',
                                                                        'bloom_level': 'knowledge'
                                                                    }
                                                                    def _create_fallback_short_answer(self,sentences:str,question_id:int,difficulty:str)-> Dict:
                                                                          """Create a fallback short answer type """
                                                                          return{
                                                                                'id': question_id,
                                                                                 'type': 'short_answer',
                                                                                 'question':f"Explain the main concept described in '{sentences[:60]}...'",
                                                                                 'sample_answer':sentences,
                                                                                 'explanation':"Answer should demonstrate understanding of the key concept mentioned.",
                                                                                 'difficulty':difficulty,
                                                                                 'points': 2,
                                                                                 'topic': 'Content Understanding',
                                                                                 'bloom_level': 'comprehension'
                                                                          }
                                                                    

                                                                    def _create_fallback_essay(self,sentences:str,question_id:int,difficulty:str)-> Dict:
                                                                          """Create a fallback essay type """
                                                                          return{
                                                                                'id': question_id,
                                                                                 'type': 'essay',
                                                                                 'question':f"Discuss the main themes and concepts presented in the provided Content '{sentences[:300]}...'",
                                                                                 'sample_answer':sentences,
                                                                                 'explanation':"Answer should demonstrate comprehensive understanding and critical analysis of the content.",
                                                                                 'difficulty':difficulty,
                                                                                 'points': 5,
                                                                                 'topic': 'Content Analysis',
                                                                                 'bloom_level': 'analysis'
                                                                          }
                                                                    def  generated_questions_with_config(self,content: str, config: Dict, client_features: Dict, client_feature : Dict=None) -> List[Dict]:
                                                                        """Generate questions with specific configuration"""
                                                                        all_questions = []
                                                                        total_questions = 0
                                                                        # calculated total question needed
                                                                        for q_type,settings in config.items():
                                                                              if not settings.get('enabled', True):
                                                                                  continue
                                                                              count = settings.get('count', 0)
                                                                              difficulty = settings.get('difficulty', 'medium')
                                                                              if count > 0:
                                                                                 try :
                                                                                      type_questions = self.generate_questions(content,q_type, count, difficulty)
                                                                                      all_questions.extend(type_questions)
                                                                                 except Exception as e:
                                                                                      logger.error(f"Failed to generate questions for {q_type} questions: {e}")

                                                                                      for i, question in enumerate(type_questions): question['id'] = i + 1
                                                                                      logger.info(f"Generated {len(all_questions)} questions with custom configuration ")
                                                                                      return all_questions
                                                                                 
                                                                        def _generate_specific_type_questions(self,content : str , q_type : str , count : int , difficulty: str )-> list(Dict):
                                                                              """Generate questions of a specific type"""
                                                                              if self.model:
                                                                                            #  use ai modle to generate specific question
                                                                                            prompt = self._create_specific_type_prompt(content, q_type, count, difficulty)
                                                                                            try:
                                                                                                  response = self.model.generate_content(prompt)
                                                                                                  questions_data = self._parse_ai_response(response.text)
                                                                                                  if questions_data and 'questions=' in questions_data:
                                                                                                      validated_questions = []
                                                                                                      for i, question in enumerate(questions_data['questions'][:count]):
                                                                                                            validated_question = self._validate_and_clean_question(question, i + 1)
                                                                                                            if validated_question:
                                                                                                                validated_questions.append(validated_question)
                                                                                                      return validated_questions
                                                                                            except Exception as e:
                                                                                                  logger.error(f"generation failed for {q_type} questions: {e}")
                                                                                                  return self._generate_fallback_questions(content, q_type, count, difficulty)
                                                                        def _create_specific_type_prompt(self, content: str, q_type: str, count: int, difficulty: str) -> str:
                                                                              """Create prompt for specific question type """
                                                                              type_instructions = {
            'mcq': f"""
Generate {count} multiple choice questions with exactly 4 options each.
Each question must have ONE correct answer and three plausible distractors.
Format each as: {{"type": "mcq", "question": "...", "options": ["A) ...", "B) ...", "C) ...", "D) ..."], "correct_answer": "A", ...}}
            """,
            'short_answer': f"""
Generate {count} short answer questions requiring 1-3 sentence responses.
Include sample answers and grading criteria.
Format each as: {{"type": "short_answer", "question": "...", "sample_answer": "...", ...}}
            """,
            'essay': f"""
Generate {count} essay questions requiring detailed analysis or discussion.
Include comprehensive sample answers and evaluation criteria.
Format each as: {{"type": "essay", "question": "...", "sample_answer": "...", ...}}
            """,
            'true_false': f"""
Generate {count} true/false questions based on factual statements from the content.
Format each as: {{"type": "true_false", "question": "...", "correct_answer": true, ...}}
            """,
            'fill_blanks': f"""
Generate {count} fill-in-the-blank questions with 1-3 blanks per question.
Format each as: {{"type": "fill_blanks", "question": "The ___ is ...", "blanks": ["answer1", "answer2"], ...}}
            """
        }
                    instructions = type_instructions.get(q_type, type)
                    return f"""Based on this content , {instructions} content : {content [:2000]} Difficulty :{difficulty} Return only the valid JSON:
                    {{"questions": [...]}}"""

                #  END OF THIS ISLAND .Ufffffffff.............
=======
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
>>>>>>> rohan
