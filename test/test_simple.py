"""
Simplified test for Question Generator - Tests basic functionality
Run this after dependencies are installed
"""

import os
import sys
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 60)
print("SIMPLIFIED RAG QUESTION GENERATOR TEST")
print("=" * 60)

# Test 1: Import Check
print("\n[TEST 1] Checking imports...")
try:
    from backend.questions import QuestionGenerator
    print("✓ QuestionGenerator imported successfully")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    print("\nPlease install dependencies:")
    print("  pip install sentence-transformers faiss-cpu")
    sys.exit(1)

# Test 2: Initialize Generator
print("\n[TEST 2] Initializing Question Generator...")
try:
    qg = QuestionGenerator()
    print("✓ QuestionGenerator initialized")
    
    # Check RAG engine
    if qg.rag_engine:
        stats = qg.get_rag_stats()
        print(f"✓ RAG Engine ready: {stats['total_chunks']} chunks")
    else:
        print("⚠ RAG Engine not available (faiss may not be installed)")
        
except Exception as e:
    print(f"✗ Initialization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Generate Questions (without RAG if needed)
print("\n[TEST 3] Generating sample questions...")

sample_text = """
Artificial Intelligence (AI) is the simulation of human intelligence by machines.
Machine Learning is a subset of AI that enables systems to learn from data.
Deep Learning uses neural networks with multiple layers to process complex patterns.
Natural Language Processing (NLP) allows computers to understand human language.
"""

try:
    # Try with RAG first, fallback to without if needed
    use_rag = qg.rag_engine is not None and qg.rag_engine.index.ntotal > 0
    
    questions = qg.generate_questions(
        content=sample_text,
        num_questions=3,
        difficulty="medium",
        topic="Artificial Intelligence",
        use_rag=use_rag
    )
    
    print(f"✓ Generated {len(questions)} questions")
    
    # Test 4: Validate Metadata
    print("\n[TEST 4] Validating question metadata...")
    
    required_fields = ['id', 'type', 'question', 'difficulty', 'topic', 'taxonomy', 'grounding']
    
    for i, q in enumerate(questions, 1):
        print(f"\n--- Question {i} ---")
        print(f"Type: {q.get('type', 'N/A')}")
        print(f"Difficulty: {q.get('difficulty', 'N/A')}")
        print(f"Topic: {q.get('topic', 'N/A')}")
        print(f"Taxonomy: {q.get('taxonomy', 'N/A')}")
        print(f"Question: {q.get('question', 'N/A')[:80]}...")
        
        # Check metadata
        missing = [f for f in required_fields if f not in q]
        if missing:
            print(f"⚠ Missing fields: {missing}")
        else:
            print("✓ All required metadata present")
        
        # Show grounding info
        if 'grounding' in q:
            chunk_count = len(q['grounding'].get('chunk_ids', []))
            confidence = q['grounding'].get('confidence_score', 0)
            print(f"Grounding: {chunk_count} chunks, confidence: {confidence}")
    
    # Test 5: Export sample for Agent 4
    print("\n[TEST 5] Exporting sample questions for Agent 4...")
    
    output_file = "test/sample_questions_for_agent4.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Sample questions saved to: {output_file}")
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Review sample questions in: test/sample_questions_for_agent4.json")
    print("2. Proceed to Agent 4 handoff")
    
except Exception as e:
    print(f"\n✗ Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
