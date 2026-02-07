import sys
import os
import logging
from dotenv import load_dotenv

# Load env vars
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Setup logging to file
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s',
    filename='test_debug.log',
    filemode='w'
)
logger = logging.getLogger(__name__)

from backend.questions import QuestionGenerator

def test_question_generation():
    # Redirect stdout to file
    with open('test_gen_output.txt', 'w', encoding='utf-8') as f:
        sys.stdout = f
        
        print("\n=== Testing Question Generator ===\n")
        
        # Initialize generator
        try:
            generator = QuestionGenerator()
            print("✓ Generator initialized")
        except Exception as e:
            print(f"✗ Failed to initialize generator: {e}")
            return

        # Check model status
        if generator.model:
            print("✓ Gemini model configured (API Key present)")
        else:
            print("! Gemini model NOT configured (Using fallback)")

        # Test content
        test_content = """
        Python is a high-level, general-purpose programming language. Its design philosophy emphasizes code readability with the use of significant indentation.
        Python is dynamically typed and garbage-collected. It supports multiple programming paradigms, including structured (particularly procedural), object-oriented and functional programming.
        """

        print(f"\nGenerating questions from content ({len(test_content)} chars)...")
        
        # Generate questions
        try:
            questions = generator.generate_questions(
                content=test_content, 
                num_questions=3, 
                difficulty="medium",
                use_rag=False 
            )
            
            print(f"\nGenerated {len(questions)} questions:")
            for i, q in enumerate(questions, 1):
                print(f"\nQuestion {i} [{q.get('type', 'unknown')}]: {q.get('question')}")
                print(f"  Options: {q.get('options')}")
                print(f"  Answer: {q.get('correct_answer')}")
                print(f"  Explanation: {q.get('explanation')}")

            if len(questions) > 0:
                print("\n✓ Question generation SUCCESS")
                if generator.model:
                     print("  (Used AI Model)")
                else:
                     print("  (Used Fallback Method)")
        except Exception as e:
            print(f"\n✗ Error during generation: {e}")
            import traceback
            traceback.print_exc()
            
    # Restore stdout
    sys.stdout = sys.__stdout__

if __name__ == "__main__":
    test_question_generation()
