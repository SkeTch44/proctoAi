"""
Integration Test for Question Generation Modes

Tests all 3 modes:
1. Pure AI Generation
2. RAG + LLM Generation  
3. PDF Scan / Extraction
"""

import os
import sys
import json
import tempfile

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.question_generation_service import QuestionGenerationService
from backend.question_bank import QuestionBankManager
from backend.utils.logging_config import setup_logging

# Initialize Logging for Test
setup_logging(name="test_integration", log_file="test_integration.log")


def create_sample_pdf():
    """Create a sample question PDF for testing"""
    content = """
    Physics Exam - Chapter 3
    
    Q1. What is Newton's First Law of Motion?
    
    Q2. Which of the following is a unit of force?
    A) Meter
    B) Newton
    C) Joule
    D) Watt
    
    Q3. True or False: Friction always opposes motion.
    
    Q4. Fill in the blank: The acceleration due to gravity is approximately _____ m/s².
    
    Q5. Explain the principle of conservation of momentum.
    """
    
    # Create a text file for now (PDF would require reportlab)
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
    temp_file.write(content)
    temp_file.close()
    return temp_file.name


def test_mode1_pure_ai():
    """Test Mode 1: Pure AI Generation"""
    print("\n" + "="*60)
    print("TEST MODE 1: PURE AI GENERATION")
    print("="*60)
    
    service = QuestionGenerationService()
    
    result = service.generate_pure_ai(
        topic="Python Programming",
        count=3,
        difficulty="medium",
        question_types=["mcq"]
    )
    
    print(f"Success: {result['success']}")
    print(f"Message: {result['message']}")
    print(f"Questions generated: {result['count']}")
    print(f"Saved to bank: {result['saved_count']}")
    
    if result['questions']:
        print("\nSample question:")
        q = result['questions'][0]
        print(f"  Text: {q.get('question_text', 'N/A')[:100]}...")
        print(f"  Type: {q.get('question_type')}")
        print(f"  Difficulty: {q.get('difficulty')}")
    
    return result['success']


def test_mode2_rag():
    """Test Mode 2: RAG Generation (using text file)"""
    print("\n" + "="*60)
    print("TEST MODE 2: RAG + LLM GENERATION")
    print("="*60)
    
    # Create sample file represents a source document
    sample_file = create_sample_pdf()
    print(f"Created sample source file: {sample_file}")
    
    service = QuestionGenerationService()
    
    # Note: RAG engine might be mocked or disabled if not running, 
    # but the service should handle the fallback to full text
    result = service.generate_rag(
        file_path=sample_file,
        topic="Physics Concepts",
        count=3,
        difficulty="medium",
        question_types=["mcq", "short_answer"]
    )
    
    print(f"Success: {result['success']}")
    print(f"Message: {result['message']}")
    print(f"Questions generated: {result['count']}")
    
    if 'document_chars' in result:
        print(f"Document chars extracted: {result['document_chars']}")
        
    print(f"Saved to bank: {result['saved_count']}")
    
    if result['questions']:
        print("\nGenerated question from doc:")
        q = result['questions'][0]
        print(f"  Text: {q.get('question_text', 'N/A')[:100]}...")
        print(f"  Type: {q.get('question_type')}")
        print(f"  Source: {q.get('metadata', {}).get('source_document', 'N/A')}")
    
    # Cleanup
    # os.unlink(sample_file) # Re-used in next test or cleanup there
    
    return result['success']


def test_mode3_pdf_scan():
    """Test Mode 3: PDF Scan (using text file)"""
    print("\n" + "="*60)
    print("TEST MODE 3: PDF SCAN / EXTRACTION")
    print("="*60)
    
    # Create sample file
    sample_file = create_sample_pdf()
    print(f"Created sample file: {sample_file}")
    
    service = QuestionGenerationService()
    
    # Note: This will use the question parser on the text content
    # For actual PDFs, the MultiLayerPDFExtractor would be used
    result = service.scan_pdf(
        file_path=sample_file,
        topic="Physics Chapter 3"
    )
    
    print(f"Success: {result['success']}")
    print(f"Message: {result['message']}")
    print(f"Questions extracted: {result['count']}")
    print(f"Saved to bank: {result['saved_count']}")
    
    if result['questions']:
        print("\nExtracted questions:")
        for i, q in enumerate(result['questions'][:3], 1):
            print(f"  {i}. {q.get('question_text', 'N/A')[:60]}...")
            print(f"     Type: {q.get('question_type')}")
    
    # Cleanup
    os.unlink(sample_file)
    
    return result['success']


def test_question_bank_storage():
    """Verify questions are stored in question bank"""
    print("\n" + "="*60)
    print("TEST: QUESTION BANK STORAGE")
    print("="*60)
    
    qb_manager = QuestionBankManager('exam_platform.db')
    
    # Search for recently added questions
    result = qb_manager.search_questions(
        filters={'topic': 'Python Programming'},
        page=1,
        per_page=5
    )
    
    print(f"Found {result['total']} questions for 'Python Programming'")
    
    if result['questions']:
        print("\nStored questions:")
        for q in result['questions'][:3]:
            print(f"  - [{q.question_type}] {q.question_text[:50]}...")
    
    return result['total'] > 0


def test_bulk_create():
    """Test bulk_create_questions"""
    print("\n" + "="*60)
    print("TEST: BULK CREATE QUESTIONS")
    print("="*60)
    
    from backend.question_bank import Question
    
    qb_manager = QuestionBankManager('exam_platform.db')
    
    # Create test questions
    questions = [
        Question(
            question_text="What is 2+2?",
            question_type="mcq",
            topic="Math",
            difficulty="easy",
            points=1,
            question_data={"options": {"A": "3", "B": "4", "C": "5", "D": "6"}, "correct_answer": "B"}
        ),
        Question(
            question_text="What is the capital of France?",
            question_type="short_answer",
            topic="Geography",
            difficulty="easy",
            points=1,
            question_data={"expected_answer": "Paris"}
        ),
        Question(
            question_text="Explain photosynthesis in plants.",
            question_type="essay",
            topic="Biology",
            difficulty="medium",
            points=5
        )
    ]
    
    result = qb_manager.bulk_create_questions(questions)
    
    print(f"Created: {result['created_count']}")
    print(f"Failed: {result['failed_count']}")
    print(f"IDs: {result['question_ids']}")
    
    return result['created_count'] > 0


def run_all_tests():
    """Run all integration tests"""
    print("\n" + "#"*60)
    print("# QUESTION GENERATION MODES - INTEGRATION TEST")
    print("#"*60)
    
    results = {
        "Mode 1 (Pure AI)": test_mode1_pure_ai(),
        "Mode 2 (RAG + LLM)": test_mode2_rag(),
        "Mode 3 (PDF Scan)": test_mode3_pdf_scan(),
        "Bulk Create": test_bulk_create(),
        "Question Bank Storage": test_question_bank_storage()
    }
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + ("All tests passed! ✅" if all_passed else "Some tests failed ❌"))
    return all_passed


if __name__ == "__main__":
    run_all_tests()
