import os 
import json
import re
import logging
from typing import List, Dict,Optional
import google.generativeai as genai

from datetime import datetime


logger = logging.getLogger(__name__)

class QuetstionGenerator:
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

                                                                    # def _generate_fallback_question(self, content: str, num_questions: int, difficulty: str) -> List[Dict]: