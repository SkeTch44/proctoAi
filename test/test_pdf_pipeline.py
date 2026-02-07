
import pytest
import os
import json
import sqlite3
from unittest.mock import MagicMock, patch
from backend.utils.semantic_chunker import SemanticChunker
from backend.utils.qa_linker import QALinker
from backend.utils.pdf_classifier import PDFChunkClassifier
from backend.validator import Validator
from backend.db.database import DatabaseManager

# --- Mock Data ---
SAMPLE_BLOCKS = [
    {"text": "Q1. What is the capital of France?", "page": 1, "font_size": 12, "block_id": "b1"},
    {"text": "(A) London", "page": 1, "font_size": 11, "block_id": "b2"},
    {"text": "(B) Paris", "page": 1, "font_size": 11, "block_id": "b3"},
    {"text": "Answer: (B) Paris", "page": 1, "font_size": 11, "block_id": "b4"},
    {"text": "Explanation: Paris is the capital.", "page": 1, "font_size": 10, "block_id": "b5"}
]

@pytest.fixture
def chunker():
    return SemanticChunker()

@pytest.fixture
def linker():
    return QALinker()

@pytest.fixture
def mock_rag():
    rag = MagicMock()
    # Mock encoding: identical text -> identical vector
    rag.model.encode.side_effect = lambda texts, **kwargs: [
        __import__('numpy').array([len(t) for _ in range(384)]) for t in texts
    ]
    return rag

# --- Tests ---

def test_semantic_chunker(chunker):
    """Test that chunker groups blocks correctly"""
    chunks = chunker.chunk(SAMPLE_BLOCKS)
    
    # Expect 1 chunk because they are all small and related? 
    # Or maybe split Q vs Answer?
    # Our logic splits on Q start.
    assert len(chunks) >= 1
    first_chunk = chunks[0]
    assert "Q1." in first_chunk["text"]
    assert first_chunk["type_hint"] == "possible_question"
    assert first_chunk["confidence"] > 0.5
    
def test_classifier_fallback():
    """Test classifier fallback logic without actual LLM"""
    classifier = PDFChunkClassifier()
    # Mock successful LLM response
    with patch('requests.post') as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "response": '{"type": "QUESTION", "confidence": 0.95}'
        }
        
        result = classifier.classify("What is X?")
        assert result["type"] == "QUESTION"
        assert result["confidence"] == 0.95

def test_qa_linker(linker, mock_rag):
    """Test the linking logic"""
    questions = [{
        "text": "Q1. What is X?",
        "page": 1,
        "chunk_id": "q1",
        "confidence": 0.9
    }]
    answers = [{
        "text": "Answer: X is Y.",
        "page": 1,
        "chunk_id": "a1",
        "confidence": 0.9
    }]
    
    links = linker.link_questions_answers(questions, answers, mock_rag)
    
    assert len(links) == 1
    assert links[0]["question"]["chunk_id"] == "q1"
    assert links[0]["answer"]["chunk_id"] == "a1"
    assert links[0]["confidence"] > 0.5

def test_validator_pdf():
    """Test validator logic"""
    # Valid Case
    valid_links = [{
        "question": {"text": "Q1...", "confidence": 0.9},
        "answer": {"text": "Ans...", "confidence": 0.9},
        "confidence": 0.9
    }]
    res = Validator.validate_pdf_exam(valid_links)
    assert res["valid"] is True
    
    # Invalid Case (Empty Answer)
    invalid_links = [{
        "question": {"text": "Q1...", "confidence": 0.9},
        "answer": {"text": "", "confidence": 0.0}, # Empty
        "confidence": 0.5
    }]
    res = Validator.validate_pdf_exam(invalid_links)
    assert res["valid"] is False
    assert "empty answers" in res["errors"][0]

def test_secure_storage():
    """Test DB split storage"""
    db = DatabaseManager("sqlite:///:memory:")
    db.init_database()
    
    # Override exam creation to use generated source type (manual insert for test)
    # Actually create_exam handles basic insertion, we need to manual insert exam with source_type
    conn = db.get_connection()
    conn.execute("INSERT INTO exams (title, questions, source_type) VALUES (?, ?, ?)", ("Test PDF Exam", "[]", "pdf_extracted"))
    exam_id = 1
    conn.commit()
    conn.close()
    
    q_data = {
        "question_id": "q1",
        "text": "What is 2+2?",
        "type": "mcq",
        "options": ["3", "4"],
        "page": 1,
        "chunk_id": "c1"
    }
    a_data = {
        "correct_answer": "4",
        "explanation": "Math",
        "confidence": 1.0,
        "source_page": 1,
        "source_chunk_id": "c2"
    }
    
    # Save
    success = db.save_pdf_exam_pair(str(exam_id), q_data, a_data, admin_id=1)
    assert success is True
    
    # Verify Split
    student_view = db.get_exam_questions_for_student(str(exam_id))
    assert len(student_view) == 1
    assert student_view[0]['question_text'] == "What is 2+2?"
    assert 'correct_answer' not in student_view[0] # SECURITY CHECK
    
    grading_view = db.get_answer_for_grading("q1")
    assert grading_view['correct_answer'] == "4" # SECURITY CHECK
