
import os
import sys
import json
import logging
from pprint import pprint

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.grading import GradingEngine
from backend.questions import QuestionGenerator

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_grading_integration():
    logger.info("Initializing Grading Engine...")
    grader = GradingEngine(model_name='all-MiniLM-L6-v2')
    
    # 1. Simulate a Generated Question (as expected from Gemini)
    generated_q = {
        "id": "test_q_1",
        "type": "short_answer",
        "question": "What is the primary function of the mitochondria?",
        "sample_answer": "The mitochondria is known as the powerhouse of the cell because it generates most of the cell's supply of adenosine triphosphate (ATP), used as a source of chemical energy.",
        "difficulty": "medium",
        "points": 5,
        "topic": "Biology",
    }
    
    logger.info("Test Question:")
    logger.info(json.dumps(generated_q, indent=2))
    
    # 2. Simulate User Answers
    scenarios = [
        {
            "name": "Excellent Answer",
            "ans": "Mitochondria are the powerhouses of the cell. They generate ATP which provides energy for cellular functions."
        },
        {
            "name": "Partial Answer",
            "ans": "It makes energy for the cell."
        },
        {
            "name": "Irrelevant Answer",
            "ans": "The mitochondria is the control center of the cell and holds DNA." # Actually describing nucleus
        }
    ]
    
    print("\n" + "="*60)
    print("GRADING SCENARIOS")
    print("="*60)
    
    for scenario in scenarios:
        score, feedback = grader.grade_question(generated_q, scenario['ans'])
        print(f"\nScenario: {scenario['name']}")
        print(f"User Answer: {scenario['ans']}")
        print(f"Score: {score}/{generated_q['points']}")
        print(f"Feedback: {feedback}")
        
    logger.info("\nIntegration Test Complete")

if __name__ == "__main__":
    test_grading_integration()
