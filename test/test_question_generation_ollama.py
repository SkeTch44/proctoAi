import sys
import os
import logging
from dotenv import load_dotenv

# Load env vars
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from backend.questions import QuestionGenerator
from backend.utils.llm_client import LLMFactory, OllamaClient

def test_ollama_integration():
    print("\n=== Testing Ollama Integration ===\n")
    
    # 1. Test Factory Resolution
    print("1. Testing LLM Factory Resolution...")
    client = LLMFactory.create_client()
    
    if isinstance(client, OllamaClient):
        print("✓ Factory correctly returned OllamaClient")
    else:
        print(f"⚠ Factory returned {type(client)} (Expected OllamaClient if Ollama is running)")
        if client is None:
             print("✗ Factory returned None! Is Ollama running?")
             return

    # 2. Test QuestionGenerator Initialization
    print("\n2. Testing QuestionGenerator Initialization...")
    try:
        qg = QuestionGenerator()
        if isinstance(qg.llm_client, OllamaClient):
             print("✓ QuestionGenerator using OllamaClient")
        else:
             print(f"⚠ QuestionGenerator using {type(qg.llm_client)}")
    except Exception as e:
        print(f"✗ Failed to init QuestionGenerator: {e}")
        return

    # 3. Test Generation
    print("\n3. Testing Question Generation (Local Llama)...")
    content = """
    Artificial Intelligence (AI) is intelligence demonstrated by machines, as opposed to natural intelligence displayed by animals including humans.
    Leading AI textbooks define the field as the study of "intelligent agents": any system that perceives its environment and takes actions that maximize its chance of achieving its goals.
    Some popular accounts use the term "artificial intelligence" to describe machines that mimic "cognitive" functions that humans associate with the human mind, such as "learning" and "problem solving".
    """
    
    try:
        questions = qg.generate_questions(
            content=content,
            num_questions=1,
            difficulty="easy",
            use_rag=False
        )
        
        print(f"✓ Generated {len(questions)} questions")
        if len(questions) > 0:
            q = questions[0]
            print(f"  Question: {q.get('question')}")
            print(f"  Type: {q.get('type')}")
            print(f"  Sources: {q.get('grounding', {}).get('chunk_ids')}")
            
    except Exception as e:
        print(f"✗ Generation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ollama_integration()
