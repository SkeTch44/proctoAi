import os 
import json
import re
import logging
from typing import List, Dict,Optional
import google.generativeai as genai

from datetime import datetime


logger = logging.getLogger(__name__)

class QuestionGenerator:
    """ MAIN AI - Powered question generation system using gemini"""
    def __init__(self):
        self.model = None
        self.fallback_enabled = True


        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel("gemini-1.5-flash")
                logger.info("model initialized successfully")
            except Exception as e:
                logger.error(f"failed to initialize model : {e}")
                self.model = None

            else:
                    logger.warning("API key not found. Fallback to default model.")
        
            def generate_questions(self, content: str, num_questions: int = 10,
                                   difficulty: str = "medium") -> List[Dict]:
                """Generate questions from content using AI or fallback methods"""
        
                if not content or len(content.strip()) < 50:
                    logger.error("content too short for question generation")
                    return []
                try:
                    return self._generate_ai_questions(content, num_questions, difficulty)  
                except Exception as e:
                    logger.error(f"failed to generate questions: {e}")
                    if self.fallback_enabled:
                        return self._fallback_generate_questions(content, num_questions, difficulty)
                    return []
                else:
                    return
                self.generate_questions(content, num_questions, difficulty)

                def _generate_ai_questions(self, content: str, num_questions: int, difficulty: str) -> List[Dict]:
                    """Generate question using gemini AI model"""
                

                #create  a compereshive promt for diverse question type 


                prompt = self._create_generation_prompt(content, count , difficulty)

                try:
                    response = self._create_generation_prompt(content,count,difficulty)
                    if not response or not response.text:
                        raise Exception("Empty response from AI model")

                    # parse the Json responses
                    question_data = self._parse_question_data(response.text)

                    if not question_data or 'questions' not in question_data:
                        raise Exception("Invalid response format from AI model")

                    questions = question_data['questions']
                    
                    # validat and clean question

                    validated_questions = []
                    for i, question in enumerate(questions[:count]):
                        validated_questions.append(self._validate_and_clean_question(question,i +1))
                        if validated_questions:
                            validated_questions.append(validated_questions)

                            logger.info(f"Generated {len(validated_questions)} AI questions from content")
                            return  validated_questions
                        
                except Exception as e:
                    logger.error(f"AI questions generation error: {e}")
                    raise
                def _create_generation_prompt(self, content: str, count: int, difficulty: str) -> str:
                    """Create a prompt for the AI model to generate questions"""
                    prompt =  f""" Based on the following content, generate excatly {count} diverse exam questions at {difficulty} difficulty level.
                    content to analyze:
                     {content[:4000]} # Truncated very long content

                     Requirements:
1. Create a mix of question types: 60% Multiple Choice, 25% Short Answer, 15% Essay
2. Questions should test different cognitive levels: knowledge, comprehension, application, analysis
3. For Multiple Choice: provide exactly 4 options (A, B, C, D) with only ONE correct answer
4. Make incorrect options (distractors) plausible but clearly wrong
5. Include detailed explanations for correct answers
6. Ensure questions are directly based on the provided content
7. Vary difficulty within the {difficulty} level

Difficulty Guidelines:
- Easy: Direct recall, basic comprehension
- Medium: Application of concepts, comparison, explanation
- Hard: Analysis, synthesis, evaluation, complex problem-solving

Return ONLY valid JSON in this exact format:
{{
  "questions": [
    {{
      "id": 1,
      "type": "mcq",
      "question": "Clear, specific question text?",
      "options": ["A) First option", "B) Second option", "C) Third option", "D) Fourth option"],
      "correct_answer": "A",
      "explanation": "Detailed explanation of why A is correct and others are wrong",
      "difficulty": "{difficulty}",
      "points": 1,
      "topic": "Main topic area",
      "bloom_level": "knowledge|comprehension|application|analysis"
    }},
    {{
      "id": 2,
      "type": "short_answer",
      "question": "Question requiring brief explanation?",
      "sample_answer": "Expected answer with key points",
      "explanation": "Grading criteria and key concepts to look for",
      "difficulty": "{difficulty}",
      "points": 2,
      "topic": "Main topic area",
      "bloom_level": "comprehension|application"
    }},
    {{
      "id": 3,
      "type": "essay",
      "question": "Question requiring detailed analysis or discussion?",
      "sample_answer": "Comprehensive expected response",
      "explanation": "Evaluation criteria and key points",
      "difficulty": "{difficulty}",
      "points": 5,
      "topic": "Main topic area",
      "bloom_level": "analysis|synthesis|evaluation"
    }}
  ]
}}

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