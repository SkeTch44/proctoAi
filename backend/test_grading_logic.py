"""
Test script for enhanced GradingEngine with partial credit and cheating detection.
Tests various scenarios including exact matches, paraphrasing, and AI-style answers.
"""

import sys
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from grading import GradingEngine


def test_grading_engine():
    """Run comprehensive tests on the grading engine"""
    
    print("=" * 80)
    print("GRADING ENGINE TEST SUITE")
    print("=" * 80)
    
    # Initialize engine
    engine = GradingEngine()
    
    # Test Case 1: Exact Match (should flag EXACT_MATCH)
    print("\n[TEST 1] Exact Match Detection")
    print("-" * 80)
    
    q1 = {
        'id': 1,
        'type': 'short_answer',
        'points': 10,
        'sample_answer': 'Photosynthesis is the process by which green plants use sunlight to synthesize nutrients from carbon dioxide and water.'
    }
    
    ans1 = 'Photosynthesis is the process by which green plants use sunlight to synthesize nutrients from carbon dioxide and water.'
    
    score1, feedback1 = engine._grade_short_answer(q1, ans1)
    print(f"Question: {q1['sample_answer'][:50]}...")
    print(f"Answer: {ans1[:50]}...")
    print(f"Score: {score1}/{q1['points']}")
    print(f"Feedback: {feedback1}")
    
    # Test Case 2: Good Paraphrase (should score high, no flags)
    print("\n[TEST 2] Good Paraphrase")
    print("-" * 80)
    
    q2 = {
        'id': 2,
        'type': 'short_answer',
        'points': 10,
        'sample_answer': 'The mitochondria is the powerhouse of the cell, responsible for producing ATP through cellular respiration.'
    }
    
    ans2 = 'Mitochondria generate energy for cells by creating ATP via the process of cellular respiration.'
    
    score2, feedback2 = engine._grade_short_answer(q2, ans2)
    print(f"Question: {q2['sample_answer'][:50]}...")
    print(f"Answer: {ans2[:50]}...")
    print(f"Score: {score2}/{q2['points']}")
    print(f"Feedback: {feedback2}")
    
    # Test Case 3: AI Paraphrase (high semantic, low lexical - should flag)
    print("\n[TEST 3] AI Paraphrase Detection")
    print("-" * 80)
    
    q3 = {
        'id': 3,
        'type': 'short_answer',
        'points': 10,
        'sample_answer': 'Climate change refers to long-term shifts in temperatures and weather patterns, mainly caused by human activities, especially the burning of fossil fuels.'
    }
    
    # Synonym-heavy paraphrase
    ans3 = 'Global warming pertains to extended-duration alterations in thermal conditions and meteorological configurations, predominantly triggered by anthropogenic endeavors, particularly combustion of hydrocarbon resources.'
    
    score3, feedback3 = engine._grade_short_answer(q3, ans3)
    print(f"Question: {q3['sample_answer'][:50]}...")
    print(f"Answer: {ans3[:50]}...")
    print(f"Score: {score3}/{q3['points']}")
    print(f"Feedback: {feedback3}")
    
    # Test Case 4: Partial Understanding
    print("\n[TEST 4] Partial Understanding")
    print("-" * 80)
    
    q4 = {
        'id': 4,
        'type': 'short_answer',
        'points': 10,
        'sample_answer': 'DNA replication is a biological process that occurs in all living organisms to copy their DNA, ensuring genetic information is passed to daughter cells.'
    }
    
    ans4 = 'DNA makes copies of itself in cells.'
    
    score4, feedback4 = engine._grade_short_answer(q4, ans4)
    print(f"Question: {q4['sample_answer'][:50]}...")
    print(f"Answer: {ans4}")
    print(f"Score: {score4}/{q4['points']}")
    print(f"Feedback: {feedback4}")
    
    # Test Case 5: Irrelevant Answer
    print("\n[TEST 5] Irrelevant Answer")
    print("-" * 80)
    
    q5 = {
        'id': 5,
        'type': 'short_answer',
        'points': 10,
        'sample_answer': 'Newton\'s first law states that an object at rest stays at rest and an object in motion stays in motion unless acted upon by an external force.'
    }
    
    ans5 = 'I like pizza and video games.'
    
    score5, feedback5 = engine._grade_short_answer(q5, ans5)
    print(f"Question: {q5['sample_answer'][:50]}...")
    print(f"Answer: {ans5}")
    print(f"Score: {score5}/{q5['points']}")
    print(f"Feedback: {feedback5}")
    
    # Test Case 6: Essay Grading
    print("\n[TEST 6] Essay Grading")
    print("-" * 80)
    
    q6 = {
        'id': 6,
        'type': 'essay',
        'points': 20,
        'ideal_length': 150,
        'sample_answer': 'The Industrial Revolution was a period of major industrialization and innovation during the late 1700s and early 1800s. It began in Great Britain and quickly spread throughout the world. This time period saw the mechanization of agriculture and textile manufacturing and a revolution in power, including steam ships and railroads, that effected social, cultural and economic conditions.'
    }
    
    ans6 = 'The Industrial Revolution marked a significant transformation in manufacturing and technology during the 18th and 19th centuries. Starting in Britain, it introduced mechanized production methods, particularly in textiles and agriculture. The era witnessed revolutionary changes in transportation through steam-powered ships and railways, fundamentally altering society, economy, and culture across the globe. This period laid the foundation for modern industrial society.'
    
    score6, feedback6 = engine._grade_essay(q6, ans6)
    print(f"Question: {q6['sample_answer'][:50]}...")
    print(f"Answer: {ans6[:50]}...")
    print(f"Score: {score6}/{q6['points']}")
    print(f"Feedback: {feedback6}")
    
    # Full Exam Test
    print("\n[TEST 7] Full Exam Grading")
    print("-" * 80)
    
    questions = [q1, q2, q3, q4, q5, q6]
    answers = {
        '1': ans1,
        '2': ans2,
        '3': ans3,
        '4': ans4,
        '5': ans5,
        '6': ans6
    }
    
    result = engine.grade_exam(questions, answers)
    
    print("\nFULL EXAM RESULT:")
    print(json.dumps(result, indent=2))
    
    print("\n" + "=" * 80)
    print("TEST SUITE COMPLETE")
    print("=" * 80)


if __name__ == '__main__':
    test_grading_engine()
