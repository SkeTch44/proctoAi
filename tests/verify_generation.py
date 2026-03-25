import sys
import os
import json
import logging

# Add project root to path
sys.path.append(os.getcwd())

from backend.engine.questions import QuestionGenerator

# Setup logging
logging.basicConfig(level=logging.INFO)

def verify_generation():
    print("\nXXX_TEST_START_XXX")
    print("Initializing QuestionGenerator...")
    try:
        qg = QuestionGenerator()
        
        sample_text = """
        Machine learning is a field of inquiry devoted to understanding and building methods that 'learn', 
        that is, methods that leverage data to improve performance on some set of tasks. 
        It is seen as a part of artificial intelligence. 
        Machine learning algorithms build a model based on sample data, known as training data, 
        in order to make predictions or decisions without being explicitly programmed to do so.
        """
        
        print(f"Generating questions from text ({len(sample_text)} chars)...")
        questions = qg.generate_questions(
            content=sample_text, 
            num_questions=2, 
            difficulty="medium", 
            topic="Machine Learning"
        )
        
        print(f"\nGenerations Result: {len(questions)} questions")
        print(json.dumps(questions, indent=2))
        
        if len(questions) > 0 and 'question' in questions[0]:
            print("\n✅ SUCCESS: AI generated valid questions.")
        else:
            print("\n❌ FAILURE: No questions generated or invalid format.")
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    print("XXX_TEST_END_XXX")

if __name__ == "__main__":
    verify_generation()
