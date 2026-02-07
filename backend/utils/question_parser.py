"""
Question Parser - Extract questions from PDFs

Detects question patterns in text extracted from PDFs:
- Numbered questions (1., 2., Q1, Q2, Question 1)
- MCQ options (A), B), a., b., (a), (b))
- True/False questions
- Fill in the blanks (_____, ______)
- Short answer / Essay markers
"""

import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class DetectedQuestionType(Enum):
    MCQ = "mcq"
    TRUE_FALSE = "true_false"
    FILL_BLANKS = "fill_blanks"
    SHORT_ANSWER = "short_answer"
    ESSAY = "essay"
    MATCHING = "matching"
    UNKNOWN = "unknown"


@dataclass
class ParsedQuestion:
    """Represents a question extracted from a PDF"""
    question_number: int
    question_text: str
    question_type: DetectedQuestionType
    options: Dict[str, str] = field(default_factory=dict)  # For MCQ: {"A": "...", "B": "..."}
    correct_answer: Optional[str] = None  # If detectable
    marks: Optional[int] = None
    page_number: Optional[int] = None
    confidence: float = 0.0  # 0-1 confidence score


class QuestionParser:
    """
    Parse extracted PDF content to detect and extract questions.
    
    Supports multiple question formats and patterns commonly found in exam papers.
    """
    
    # Question number patterns
    QUESTION_PATTERNS = [
        r'^(?:Q(?:uestion)?\.?\s*)?(\d+)\s*[.):]\s*(.+)',  # Q1. or Question 1: or 1.
        r'^(?:Q(?:uestion)?\.?\s*)?(\d+)\s*\]\s*(.+)',      # Q1] format
        r'^\[(\d+)\]\s*(.+)',                               # [1] format
        r'^(?:Part\s+)?([A-Z])\s*[.):]\s*(.+)',            # Part A. or A)
    ]
    
    # MCQ option patterns
    OPTION_PATTERNS = [
        r'^([A-Da-d])\s*[.):\]]\s*(.+)',     # A) or a. or A: or A]
        r'^\(([A-Da-d])\)\s*(.+)',            # (A) or (a)
        r'^([i-v]+)\s*[.)]\s*(.+)',           # Roman numerals i) ii)
    ]
    
    # True/False patterns
    TRUE_FALSE_PATTERNS = [
        r'\b(True\s+or\s+False|T\s*/\s*F|True/False)\b',
        r'\bState\s+(?:whether|if)\s+.*\s+(?:true|false)\b',
    ]
    
    # Fill in the blanks patterns
    FILL_BLANKS_PATTERNS = [
        r'_{3,}',          # _____ (3 or more underscores)
        r'\[\.{3,}\]',     # [...] 
        r'\(\s*\)',        # Empty parentheses
        r'<blank>',        # <blank> marker
    ]
    
    # Marks/Points patterns
    MARKS_PATTERNS = [
        r'\[(\d+)\s*(?:marks?|pts?|points?)\]',
        r'\((\d+)\s*(?:marks?|pts?|points?)\)',
        r'(?:marks?|pts?|points?)\s*[:=]\s*(\d+)',
    ]
    
    def __init__(self):
        self.compiled_question_patterns = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in self.QUESTION_PATTERNS]
        self.compiled_option_patterns = [re.compile(p, re.IGNORECASE) for p in self.OPTION_PATTERNS]
        self.compiled_tf_patterns = [re.compile(p, re.IGNORECASE) for p in self.TRUE_FALSE_PATTERNS]
        self.compiled_blank_patterns = [re.compile(p) for p in self.FILL_BLANKS_PATTERNS]
        self.compiled_marks_patterns = [re.compile(p, re.IGNORECASE) for p in self.MARKS_PATTERNS]
    
    def parse(self, text_blocks: List[Dict]) -> List[ParsedQuestion]:
        """
        Parse text blocks extracted from PDF to detect questions.
        
        Args:
            text_blocks: List of dicts with 'text', 'page', 'bbox' keys
            
        Returns:
            List of ParsedQuestion objects
        """
        # Combine blocks into full text with page markers
        full_text = self._prepare_text(text_blocks)
        
        # Split into potential questions
        question_segments = self._segment_questions(full_text)
        
        # Parse each segment
        parsed_questions = []
        for i, segment in enumerate(question_segments):
            parsed = self._parse_segment(segment, i + 1)
            if parsed:
                parsed_questions.append(parsed)
        
        logger.info(f"Parsed {len(parsed_questions)} questions from {len(text_blocks)} text blocks")
        return parsed_questions
    
    def _prepare_text(self, text_blocks: List[Dict]) -> str:
        """Combine text blocks into searchable text"""
        lines = []
        current_page = 0
        
        for block in text_blocks:
            page = block.get('page', 0)
            text = block.get('text', '').strip()
            
            if page != current_page:
                lines.append(f"\n[PAGE {page}]\n")
                current_page = page
            
            if text:
                lines.append(text)
        
        return '\n'.join(lines)
    
    def _segment_questions(self, full_text: str) -> List[Dict]:
        """Split text into question segments"""
        segments = []
        lines = full_text.split('\n')
        
        current_segment = {
            'lines': [],
            'page': 1,
            'question_number': None
        }
        
        for line in lines:
            # Check for page marker
            page_match = re.match(r'\[PAGE (\d+)\]', line)
            if page_match:
                current_segment['page'] = int(page_match.group(1))
                continue
            
            # Check if this line starts a new question
            question_match = self._match_question_start(line)
            if question_match:
                # Save previous segment if it has content
                if current_segment['lines']:
                    segments.append(current_segment.copy())
                
                # Start new segment
                current_segment = {
                    'lines': [line],
                    'page': current_segment['page'],
                    'question_number': question_match.get('number')
                }
            else:
                current_segment['lines'].append(line)
        
        # Don't forget last segment
        if current_segment['lines']:
            segments.append(current_segment)
        
        return segments
    
    def _match_question_start(self, line: str) -> Optional[Dict]:
        """Check if line starts a new question"""
        line = line.strip()
        
        for pattern in self.compiled_question_patterns:
            match = pattern.match(line)
            if match:
                return {
                    'number': match.group(1),
                    'text': match.group(2) if len(match.groups()) > 1 else ''
                }
        
        return None
    
    def _parse_segment(self, segment: Dict, fallback_number: int) -> Optional[ParsedQuestion]:
        """Parse a single question segment"""
        lines = segment['lines']
        if not lines:
            return None
        
        full_text = '\n'.join(lines)
        
        # Detect question type
        q_type = self._detect_question_type(full_text)
        
        # Extract question text and options
        question_text, options = self._extract_question_and_options(lines)
        
        if not question_text or len(question_text) < 5:
            return None
        
        # Extract marks if present
        marks = self._extract_marks(full_text)
        
        # Determine question number
        q_number = segment.get('question_number')
        if q_number:
            try:
                q_number = int(q_number)
            except ValueError:
                q_number = fallback_number
        else:
            q_number = fallback_number
        
        # Calculate confidence
        confidence = self._calculate_confidence(question_text, options, q_type)
        
        return ParsedQuestion(
            question_number=q_number,
            question_text=question_text,
            question_type=q_type,
            options=options,
            marks=marks,
            page_number=segment.get('page'),
            confidence=confidence
        )
    
    def _detect_question_type(self, text: str) -> DetectedQuestionType:
        """Detect the type of question from its content"""
        # Check for True/False
        for pattern in self.compiled_tf_patterns:
            if pattern.search(text):
                return DetectedQuestionType.TRUE_FALSE
        
        # Check for Fill in blanks
        for pattern in self.compiled_blank_patterns:
            if pattern.search(text):
                return DetectedQuestionType.FILL_BLANKS
        
        # Check for MCQ options
        has_options = False
        for pattern in self.compiled_option_patterns:
            matches = pattern.findall(text)
            if len(matches) >= 2:  # At least 2 options
                has_options = True
                break
        
        if has_options:
            return DetectedQuestionType.MCQ
        
        # Check for essay/descriptive markers
        essay_markers = ['discuss', 'explain', 'describe', 'analyze', 'evaluate', 'compare', 'elaborate']
        text_lower = text.lower()
        for marker in essay_markers:
            if marker in text_lower:
                return DetectedQuestionType.ESSAY
        
        return DetectedQuestionType.SHORT_ANSWER
    
    def _extract_question_and_options(self, lines: List[str]) -> Tuple[str, Dict[str, str]]:
        """Extract question text and options from lines"""
        question_lines = []
        options = {}
        current_option = None
        current_option_text = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if this is an option line
            option_match = None
            for pattern in self.compiled_option_patterns:
                match = pattern.match(line)
                if match:
                    option_match = match
                    break
            
            if option_match:
                # Save previous option if exists
                if current_option:
                    options[current_option.upper()] = ' '.join(current_option_text)
                
                current_option = option_match.group(1)
                current_option_text = [option_match.group(2)]
            elif current_option:
                # Continue current option
                current_option_text.append(line)
            else:
                # Part of question text
                question_lines.append(line)
        
        # Save last option
        if current_option:
            options[current_option.upper()] = ' '.join(current_option_text)
        
        question_text = ' '.join(question_lines)
        
        # Clean question text - remove question number prefix
        for pattern in self.compiled_question_patterns:
            match = pattern.match(question_text)
            if match and len(match.groups()) > 1:
                question_text = match.group(2)
                break
        
        return question_text.strip(), options
    
    def _extract_marks(self, text: str) -> Optional[int]:
        """Extract marks/points from text"""
        for pattern in self.compiled_marks_patterns:
            match = pattern.search(text)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    pass
        return None
    
    def _calculate_confidence(self, question_text: str, options: Dict, q_type: DetectedQuestionType) -> float:
        """Calculate confidence score for the parsed question"""
        score = 0.0
        
        # Question text quality
        if len(question_text) > 10:
            score += 0.3
        if question_text.endswith('?'):
            score += 0.1
        
        # MCQ validation
        if q_type == DetectedQuestionType.MCQ:
            if len(options) >= 4:
                score += 0.4
            elif len(options) >= 2:
                score += 0.2
        else:
            score += 0.3  # Non-MCQ types
        
        # General quality
        if not re.search(r'[^\x00-\x7F]', question_text):  # ASCII only
            score += 0.1
        
        return min(score, 1.0)
    
    def parse_raw_text(self, raw_text: str, topic: str = "Extracted Questions") -> List[Dict]:
        """
        Convenience method to parse raw text and return question bank format.
        
        Args:
            raw_text: Plain text content
            topic: Topic name for categorization
            
        Returns:
            List of question dicts ready for QuestionBankManager
        """
        # Create fake text blocks
        text_blocks = [{'text': raw_text, 'page': 1}]
        
        parsed = self.parse(text_blocks)
        
        # Convert to question bank format
        questions = []
        for pq in parsed:
            q = {
                'question_text': pq.question_text,
                'question_type': pq.question_type.value,
                'topic': topic,
                'points': pq.marks or 1,
                'question_data': {
                    'options': pq.options,
                    'correct_answer': pq.correct_answer
                },
                'status': 'draft',
                'confidence': pq.confidence
            }
            questions.append(q)
        
        return questions
