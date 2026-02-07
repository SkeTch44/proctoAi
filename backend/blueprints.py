from typing import Dict, List

class BlueprintGenerator:
    """
    Phase 2: Blueprint Generator
    Responsibility: Define STRICT prompt templates and expected JSON schema.
    No LLM calls. Pure Python string manipulation.
    
    [UPSKILL] Now supports skill-based blueprints with skill_id tracking.
    """
    
    @staticmethod
    def get_template(batch_config: Dict, context: str = "", skill_id: str = None) -> Dict:
        """
        Returns a construct containing:
        - prompt: The strict string prompt for LLaMA
        - system_prompt: The system instruction
        - skill_id: Optional skill identifier (Upskill Architecture)
        
        Args:
            batch_config: Batch configuration with type, count, topic, difficulty
            context: Optional context from RAG or documents
            skill_id: Optional skill ID (e.g., "MCQ_GENERATION_V1")
        """
        fmt = batch_config['type']
        count = batch_config['count']
        topic = batch_config['topic']
        difficulty = batch_config['difficulty']
        
        system_prompt = "You are a strict API for exam generation. Return ONLY valid JSON."
        
        if fmt == 'mcq':
            user_prompt = f"""
TASK: Generate {count} Multiple Choice Questions (MCQ).
TOPIC: {topic}
DIFFICULTY: {difficulty}
CONTEXT: {context[:2000] if context else "General knowledge"}

RULES:
1. Each question must have meaningful text.
2. Provide exactly 4 options (A, B, C, D).
3. One correct answer.
4. Difficulty level must match '{difficulty}'.

OUTPUT SCHEMA (JSON Array):
[
  {{
    "question": "string",
    "options": {{ "A": "string", "B": "string", "C": "string", "D": "string" }},
    "answer": "A",
    "explanation": "string"
  }}
]
"""
        elif fmt == 'short_answer':
            user_prompt = f"""
TASK: Generate {count} Short Answer Questions.
TOPIC: {topic}
DIFFICULTY: {difficulty}
CONTEXT: {context[:2000] if context else "General knowledge"}

RULES:
1. Questions should require 1-3 sentences to answer.
2. Provide a sample correct answer/rubric.

OUTPUT SCHEMA (JSON Array):
[
  {{
    "question": "string",
    "sample_answer": "string",
    "explanation": "string"
  }}
]
"""
        elif fmt == 'essay' or fmt == 'descriptive':
            user_prompt = f"""
TASK: Generate {count} Essay/Long-Answer Question.
TOPIC: {topic}
DIFFICULTY: {difficulty}
CONTEXT: {context[:2000] if context else "General knowledge"}

RULES:
1. Complex question requiring deep understanding.
2. Provide key points validation rubric.

OUTPUT SCHEMA (JSON Array):
[
  {{
    "question": "string",
    "rubric_points": ["string", "string"],
    "explanation": "string"
  }}
]
"""
        else:
             # Fallback
             user_prompt = f"Generate {count} questions on {topic}."

        blueprint = {
            "system": system_prompt,
            "user": user_prompt.strip()
        }
        
        # [UPSKILL] Add skill_id if provided
        if skill_id:
            blueprint["skill_id"] = skill_id
        
        return blueprint

