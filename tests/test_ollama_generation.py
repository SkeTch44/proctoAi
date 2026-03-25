import sys
import os
import logging

# Add project root to path
sys.path.append(os.getcwd())

from backend.engine.questions import QuestionGenerator
from backend.engine.llm_runner import LLMRunner
from backend.config import Config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_questions_py_generation():
    print("\n--- Testing QuestionGenerator (backend/questions.py) ---")
    try:
        qg = QuestionGenerator()
        if not qg.llm_client:
            print("❌ LLM Client not initialized (Ollama missing?)")
            return
            
        print("✅ LLM Client initialized")
        
        # Test generation
        content = "Python is a high-level programming language. It relies on indentation for code structure."
        print(f"Generating questions for content: '{content}'")
        
        questions = qg.generate_questions(content, num_questions=1, difficulty="easy", topic="Python")
        
        if questions and len(questions) > 0:
            print(f"✅ Generated {len(questions)} questions")
            print(f"Sample: {questions[0]['question']}")
        else:
            print("❌ No questions generated")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def test_llm_runner_generation():
    print("\n--- Testing LLMRunner (backend/llm_runner.py) ---")
    try:
        blueprint_prompt = {
            "system": "You are a helpful assistant. Return JSON.",
            "user": "Generate 1 MCQ question about Python in JSON format."
        }
        batch_config = {
            "batch_id": "test_batch_1",
            "type": "mcq"
        }
        
        print(f"Running batch with model: {Config.OLLAMA_MODEL}")
        result = LLMRunner.run_batch(blueprint_prompt, batch_config)
        
        if result:
            print("✅ LLMRunner success")
            print(result)
        else:
            print("❌ LLMRunner failed (check logs)")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_questions_py_generation()
    test_llm_runner_generation()
