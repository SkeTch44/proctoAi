import os

file_path = 'backend/questions.py'

# The clean code for the rest of the file (from the rohan block)
clean_code = r'''Important: Return ONLY the JSON object, no markdown formatting, no additional text."""
        
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
'''

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Keep lines 1-272
# Line 272 in python list is index 272 (0-based) ? No, 1-based line 272 is index 271.
# The content we want ends where `<<<<<<< HEAD` begins.
# Line 273 is `<<<<<<< HEAD`. So we want lines[0:272].
# Line 272 (index 271) is the newline after `}}`.
# Line 271 (index 270) is `}}`.

new_content = "".join(lines[:272]) + clean_code

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("questions.py fixed successfully")
