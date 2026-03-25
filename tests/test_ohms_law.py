import time
import json
import logging
from backend.services.question_generation_service import QuestionGenerationService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_ohms_law_generation():
    print("=== Testing Ohm's Law Generation with Pure LLaMA ===")
    
    # Initialize Service
    try:
        service = QuestionGenerationService()
        print("[OK] Service Initialized")
    except Exception as e:
        print(f"[FAIL] Failed to initialize service: {e}")
        return

    topic = "Ohm's Law"
    requests = [
        {"type": "mcq", "count": 5},
        {"type": "short_answer", "count": 1},
        {"type": "long_answer", "count": 1}
    ]
    
    total_start_time = time.time()
    all_questions = []

    for req in requests:
        q_type = req["type"]
        count = req["count"]
        
        print(f"\n--- Generating {count} {q_type} questions ---")
        start_time = time.time()
        
        try:
            # We call the service for each specific requirement to ensure exact counts
            # as the bulk API divides counts evenly.
            result = service.generate_pure_ai(
                topic=topic,
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
                    safe_text = q.get('text', '').encode('ascii', 'ignore').decode()
                    print(f"   {i}. [{q.get('type')}] {safe_text[:100]}...")
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
    test_ohms_law_generation()
