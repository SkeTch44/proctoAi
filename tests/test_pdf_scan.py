import time
import os
import logging
from backend.services.question_generation_service import QuestionGenerationService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_pdf_scan():
    print("=== Testing PDF Scan (Question Extraction) ===")
    
    # Initialize Service
    try:
        service = QuestionGenerationService()
        print("[OK] Service Initialized")
    except Exception as e:
        print(f"[FAIL] Failed to initialize service: {e}")
        return

    # Path to PDF with existing questions
    pdf_path = "pdfcheck.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"[FAIL] PDF not found at {pdf_path}")
        return
        
    print(f"[INFO] Using source document: {pdf_path}")

    start_time = time.time()
    
    try:
        # Call PDF scan/extraction
        result = service.scan_pdf(
            file_path=pdf_path,
            topic="Extracted Questions"
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        if result.get('success'):
            qs = result.get('questions', [])
            print(f"\n[OK] Extracted {len(qs)} questions in {duration:.2f} seconds")
            
            # Display extracted questions
            for i, q in enumerate(qs, 1):
                q_type = q.get('question_type', 'unknown')
                safe_text = q.get('question_text', '').encode('ascii', 'ignore').decode()
                print(f"\n{i}. [{q_type.upper()}] {safe_text[:150]}...")
                
                # Show options if MCQ
                if q_type == 'mcq' and 'question_data' in q:
                    options = q['question_data'].get('options', {})
                    for key, val in options.items():
                        safe_opt = val.encode('ascii', 'ignore').decode()
                        print(f"   {key}) {safe_opt[:80]}")
                    correct = q['question_data'].get('correct_answer', 'N/A')
                    print(f"   Correct: {correct}")
                
                # Show metadata
                if 'metadata' in q:
                    meta = q['metadata']
                    page = meta.get('page_number', 'N/A')
                    conf = meta.get('extraction_confidence', 0)
                    print(f"   [Page: {page}, Confidence: {conf:.2f}]")
        else:
            print(f"[FAIL] Extraction failed: {result.get('message')}")
            
    except Exception as e:
        print(f"[ERROR] During extraction: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*40)
    print(f"TOTAL TIME: {duration:.2f} seconds")
    print("="*40)

if __name__ == "__main__":
    test_pdf_scan()
