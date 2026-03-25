import time
import os
import logging
from backend.services.question_generation_service import QuestionGenerationService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_rag_generation():
    print("=== Testing RAG Generation with Ohm's Law PDF ===")
    
    # Initialize Service
    try:
        service = QuestionGenerationService()
        print("[OK] Service Initialized")
    except Exception as e:
        print(f"[FAIL] Failed to initialize service: {e}")
        return

    # Path to existing PDF
    pdf_path = os.path.join("backend", "uploads", "Ohms_Law_Class_12_Notes.pdf")
    
    if not os.path.exists(pdf_path):
        print(f"[FAIL] PDF not found at {pdf_path}")
        return
        
    print(f"[INFO] Using source document: {pdf_path}")

    # Define requests: 5 MCQ, 2 Long Answer
    # Long Answer maps to 'descriptive_generation' skill internally (just verified)
    requests = [
        {"type": "mcq", "count": 5},
        {"type": "long_answer", "count": 2}
    ]
    
    total_start_time = time.time()
    all_questions = []

    for req in requests:
        q_type = req["type"]
        count = req["count"]
        
        print(f"\n--- Generating {count} {q_type} questions from PDF ---")
        start_time = time.time()
        
        try:
            # Call RAG generation
            # Note: generate_rag takes question_types list, but we call it per type to measure timings accurately
            result = service.generate_rag(
                file_path=pdf_path,
                topic="Ohm's Law", # Optional topic hint
                count=count,
                difficulty="medium",
                question_types=[q_type]
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            if result.get('success'):
                qs = result.get('questions', [])
                print(f"[OK] Generated {len(qs)} questions in {duration:.2f} seconds")
                for i, q in enumerate(qs, 1):
                    # Safe ASCII printing for Windows console
                    safe_text = q.get('question_text', '').encode('ascii', 'ignore').decode()
                    print(f"   {i}. [{q.get('question_type')}] {safe_text[:100]}...")
                all_questions.extend(qs)
            else:
                print(f"[FAIL] Generation failed: {result.get('message')}")
                
        except Exception as e:
            print(f"[ERROR] During generation: {e}")

    total_end_time = time.time()
    total_duration = total_end_time - total_start_time
    
    print("\n" + "="*40)
    print(f"TOTAL TIME: {total_duration:.2f} seconds")
    print(f"TOTAL QUESTIONS: {len(all_questions)}")
    print("="*40)

if __name__ == "__main__":
    test_rag_generation()
