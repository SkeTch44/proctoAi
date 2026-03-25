import sys
import os
import logging
import json

# Add project root to path
sys.path.append(os.getcwd())

from backend.utils.skill_compiler import get_skill_compiler
from backend.engine.llm_runner import LLMRunner

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_upskill_flow():
    print("\n--- Testing Upskill Architecture Flow ---")
    
    try:
        # 1. Get Compiler
        compiler = get_skill_compiler()
        print("✅ Compiler initialized")
        
        # 2. Compile Skill
        skill_name = "mcq_generation"
        variables = {
            "count": 1,
            "topic": "Python Lists",
            "difficulty": "easy",
            "context": "Lists are mutable sequences, typically used to store collections of homogeneous items."
        }
        
        print(f"Compiling skill '{skill_name}'...")
        packet = compiler.compile_skill(skill_name, variables)
        print(f"✅ Skill cooked: {packet.skill_id}")
        
        # 3. Execute Runner
        print("Executing via LLMRunner.execute()...")
        result = LLMRunner.execute(packet)
        
        if result:
            print("✅ Execution successful!")
            print(json.dumps(result, indent=2))
        else:
            print("❌ Execution failed (check logs)")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_upskill_flow()
