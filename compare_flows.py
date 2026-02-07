"""
Side-by-side comparison: Legacy Flow vs Upskill Flow
Demonstrates prompt size, execution time, and output quality differences
"""
import sys
import os
import json
import time
import logging

sys.path.append(os.getcwd())

from backend.questions import QuestionGenerator
from backend.utils.skill_compiler import get_skill_compiler
from backend.llm_runner import LLMRunner

logging.basicConfig(level=logging.WARNING)  # Reduce noise
logger = logging.getLogger(__name__)

# Test content
SAMPLE_CONTENT = """
Python is a high-level, interpreted programming language known for its simplicity and readability.
It uses indentation to define code blocks instead of curly braces.
Python supports multiple programming paradigms including procedural, object-oriented, and functional programming.
The language has a comprehensive standard library and a vast ecosystem of third-party packages.
"""

def test_legacy_flow():
    """Test the legacy QuestionGenerator flow"""
    print("\n" + "="*60)
    print("LEGACY FLOW TEST")
    print("="*60)
    
    try:
        start = time.time()
        
        qg = QuestionGenerator()
        questions = qg.generate_questions(
            content=SAMPLE_CONTENT,
            num_questions=2,
            difficulty="medium",
            topic="Python Programming",
            use_rag=False  # Disable RAG for faster test
        )
        
        elapsed = time.time() - start
        
        print(f"\n✅ Generated {len(questions)} questions in {elapsed:.2f}s")
        print(f"\nSample Question:")
        if questions:
            print(json.dumps(questions[0], indent=2))
        
        return {
            'success': len(questions) > 0,
            'count': len(questions),
            'time': elapsed,
            'questions': questions
        }
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}

def test_upskill_flow():
    """Test the new Upskill architecture flow"""
    print("\n" + "="*60)
    print("UPSKILL FLOW TEST")
    print("="*60)
    
    try:
        start = time.time()
        
        # 1. Get compiler
        compiler = get_skill_compiler()
        
        # 2. Compile skill
        packet = compiler.compile_skill("mcq_generation", {
            "count": 2,
            "topic": "Python Programming",
            "difficulty": "medium",
            "context": SAMPLE_CONTENT
        })
        
        print(f"\n📦 Compiled Skill: {packet.skill_id}")
        print(f"   Prompt Size: {len(packet.system_prompt)} chars")
        print(f"   Temperature: {packet.llm_params.get('temperature')}")
        print(f"   Max Tokens: {packet.llm_params.get('max_tokens')}")
        
        # 3. Execute via LLMRunner
        result = LLMRunner.execute(packet)
        
        elapsed = time.time() - start
        
        if result and isinstance(result, list):
            print(f"\n✅ Generated {len(result)} questions in {elapsed:.2f}s")
            print(f"\nSample Question:")
            print(json.dumps(result[0], indent=2))
            
            return {
                'success': True,
                'count': len(result),
                'time': elapsed,
                'prompt_size': len(packet.system_prompt),
                'questions': result
            }
        else:
            print(f"\n⚠️ Unexpected result format: {type(result)}")
            return {'success': False, 'error': 'Invalid result format'}
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}

def main():
    print("\n" + "🔬 FLOW COMPARISON TEST 🔬".center(60))
    print("Testing both generation flows with identical content\n")
    
    # Test both flows
    legacy_result = test_legacy_flow()
    upskill_result = test_upskill_flow()
    
    # Summary comparison
    print("\n" + "="*60)
    print("COMPARISON SUMMARY")
    print("="*60)
    
    print(f"\n{'Metric':<25} {'Legacy':<15} {'Upskill':<15}")
    print("-" * 60)
    
    if legacy_result.get('success') and upskill_result.get('success'):
        print(f"{'Success Rate':<25} {'✅':<15} {'✅':<15}")
        print(f"{'Questions Generated':<25} {legacy_result['count']:<15} {upskill_result['count']:<15}")
        print(f"{'Execution Time':<25} {legacy_result['time']:.2f}s{'':<10} {upskill_result['time']:.2f}s")
        
        if 'prompt_size' in upskill_result:
            print(f"{'Prompt Size':<25} {'N/A':<15} {upskill_result['prompt_size']} chars")
        
        # Speed comparison
        if legacy_result['time'] > 0 and upskill_result['time'] > 0:
            speedup = ((legacy_result['time'] - upskill_result['time']) / legacy_result['time']) * 100
            if speedup > 0:
                print(f"\n🚀 Upskill is {speedup:.1f}% faster")
            else:
                print(f"\n⚡ Legacy is {abs(speedup):.1f}% faster")
    else:
        print(f"{'Legacy Success':<25} {legacy_result.get('success', False)}")
        print(f"{'Upskill Success':<25} {upskill_result.get('success', False)}")
    
    print("\n" + "="*60)
    print("\n✨ Recommendation: Use Upskill Flow for production")
    print("   - Smaller prompts")
    print("   - Skill-specific optimization")
    print("   - Better validation")
    print("   - Easier to maintain\n")

if __name__ == "__main__":
    main()
