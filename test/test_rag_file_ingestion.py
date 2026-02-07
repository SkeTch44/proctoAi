
import os
import sys
import json
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.questions import QuestionGenerator

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_file_ingestion():
    file_path = "test/sample_test.docx"
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return

    logger.info(f"Initializing Question Generator...")
    qg = QuestionGenerator()
    
    logger.info(f"Processing document: {file_path}")
    doc_id = qg.process_document(file_path)
    
    if not doc_id:
        logger.error("Failed to process document")
        return

    logger.info(f"Document processed successfully. Doc ID: {doc_id}")
    
    # Check stats
    stats = qg.get_rag_stats()
    logger.info(f"RAG Chunk Stats: {stats}")
    
    # Generate Questions
    logger.info("Generating questions from RAG context...")
    questions = qg.generate_questions(
        content="What is Artificial Intelligence and Machine Learning?",
        num_questions=2,
        difficulty="easy",
        topic="AI Basics",
        use_rag=True
    )
    
    print("\n" + "="*50)
    print("GENERATED QUESTIONS")
    print("="*50)
    print(json.dumps(questions, indent=2))
    print("="*50)

if __name__ == "__main__":
    test_file_ingestion()
