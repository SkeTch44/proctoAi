"""
Test script for RAG-enhanced Question Generator

This script demonstrates:
1. RAG engine initialization
2. Document processing (PDF/DOCX)
3. Question generation with RAG grounding
4. Metadata validation
"""

import os
import sys
import json
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.questions import QuestionGenerator
from utils.rag_engine import RAGEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_rag_engine():
    """Test RAG engine basic functionality"""
    logger.info("=" * 60)
    logger.info("TEST 1: RAG Engine Initialization")
    logger.info("=" * 60)
    
    try:
        rag = RAGEngine(store_path="backend/db/rag_strore")
        logger.info("✓ RAG engine initialized successfully")
        
        # Test adding documents
        test_chunks = [
            "Machine learning is a subset of artificial intelligence.",
            "Neural networks are inspired by biological neurons.",
            "Deep learning uses multiple layers of neural networks."
        ]
        
        num_added = rag.add_document(
            doc_id="test_doc_1",
            chunks=test_chunks,
            metadata={"source": "test", "topic": "Machine Learning"}
        )
        
        logger.info(f"✓ Added {num_added} chunks to RAG store")
        
        # Test search
        results = rag.search("What is machine learning?", k=2)
        logger.info(f"✓ Retrieved {len(results)} chunks from search")
        
        for i, result in enumerate(results, 1):
            logger.info(f"  Result {i}: {result['text'][:50]}... (score: {result['score']:.4f})")
        
        # Get stats
        stats = rag.get_stats()
        logger.info(f"✓ RAG Stats: {stats}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ RAG engine test failed: {e}")
        return False

def test_question_generator():
    """Test question generator with RAG"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: Question Generator with RAG")
    logger.info("=" * 60)
    
    try:
        qg = QuestionGenerator()
        logger.info("✓ Question generator initialized")
        
        # Test content
        test_content = """
        Machine learning is a method of data analysis that automates analytical model building.
        It is a branch of artificial intelligence based on the idea that systems can learn from data,
        identify patterns and make decisions with minimal human intervention.
        
        Neural networks are computing systems inspired by biological neural networks.
        They consist of interconnected nodes (neurons) that process information using a connectionist
        approach to computation. Deep learning is a subset of machine learning that uses neural networks
        with multiple layers.
        """
        
        # Generate questions
        logger.info("Generating questions...")
        questions = qg.generate_questions(
            content=test_content,
            num_questions=3,
            difficulty="medium",
            topic="Machine Learning",
            use_rag=True
        )
        
        logger.info(f"✓ Generated {len(questions)} questions")
        
        # Validate metadata
        required_fields = ['id', 'type', 'question', 'difficulty', 'topic', 'taxonomy', 'grounding']
        
        for i, q in enumerate(questions, 1):
            logger.info(f"\nQuestion {i}:")
            logger.info(f"  Type: {q.get('type')}")
            logger.info(f"  Difficulty: {q.get('difficulty')}")
            logger.info(f"  Topic: {q.get('topic')}")
            logger.info(f"  Taxonomy: {q.get('taxonomy')}")
            logger.info(f"  Question: {q.get('question', '')[:80]}...")
            
            # Check required fields
            missing_fields = [field for field in required_fields if field not in q]
            if missing_fields:
                logger.warning(f"  ⚠ Missing fields: {missing_fields}")
            else:
                logger.info(f"  ✓ All required metadata present")
            
            # Check grounding
            if 'grounding' in q:
                chunk_ids = q['grounding'].get('chunk_ids', [])
                confidence = q['grounding'].get('confidence_score', 0)
                logger.info(f"  Grounding: {len(chunk_ids)} chunks, confidence: {confidence}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Question generator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_document_processing():
    """Test PDF/DOCX processing (if sample files exist)"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: Document Processing")
    logger.info("=" * 60)
    
    try:
        qg = QuestionGenerator()
        
        # Check for sample files
        test_dir = "test"
        sample_files = []
        
        if os.path.exists(test_dir):
            for file in os.listdir(test_dir):
                if file.endswith(('.pdf', '.docx')):
                    sample_files.append(os.path.join(test_dir, file))
        
        if not sample_files:
            logger.info("⚠ No sample PDF/DOCX files found in test/ directory")
            logger.info("  Skipping document processing test")
            return True
        
        for file_path in sample_files:
            logger.info(f"\nProcessing: {file_path}")
            doc_id = qg.process_document(file_path)
            
            if doc_id:
                logger.info(f"✓ Successfully processed document: {doc_id}")
            else:
                logger.warning(f"✗ Failed to process document: {file_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Document processing test failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("\n" + "=" * 60)
    logger.info("RAG-ENHANCED QUESTION GENERATOR TEST SUITE")
    logger.info("=" * 60)
    
    results = {
        'RAG Engine': test_rag_engine(),
        'Question Generator': test_question_generator(),
        'Document Processing': test_document_processing()
    }
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        logger.info(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        logger.info("\n🎉 All tests passed!")
    else:
        logger.info("\n⚠ Some tests failed. Check logs above.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
