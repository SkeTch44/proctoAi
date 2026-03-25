import json
import logging
from typing import Dict, Any, Optional
from backend.engine.llm_runner import LLMRunner

logger = logging.getLogger(__name__)

ANTIGRAVITY_QA_SYSTEM_PROMPT = """
You are Antigravity-QA, an adversarial quality assurance agent.

You do not assist the system.
You do not optimize outputs.
You do not fix errors.

Your job is to detect:
- hallucinations
- answer leakage
- incorrect extraction
- unsafe behavior
- logical inconsistencies
- violations of exam integrity

Assume the system is wrong unless proven otherwise.

You must:
- cite evidence
- return structured verdicts
- block unsafe exams

If unsure, fail conservatively.

Return JSON only.
AGENT ROLE DEFINITION
Name
Antigravity-QA

Authority Level
SYSTEM_GUARDIAN (cannot be overridden)

Allowed Actions

Read inputs / outputs

Query RAG

Compare expected vs actual

Inspect metadata

Fail pipelines

Block exam publishing

Forbidden Actions

Generating questions

Fixing answers

Suggesting content to user

Modifying ground truth

🧠 WHAT THIS AGENT CHECKS (HARD GUARANTEES)
1️⃣ PDF → QUESTION EXTRACTION QA

Checks:

❌ Question hallucination

❌ Missing questions

❌ Merged questions

❌ OCR corruption

❌ Page mismatch

Rule

If extracted question not traceable to PDF page → FAIL

2️⃣ ANSWER SAFETY QA (CRITICAL)

Checks:

Answers never appear before exam

Answers not leaked in logs

Answers not embedded in RAG during exam

Answers not derivable from question text

Rule

If answer tokens appear in student context → CRITICAL FAIL

3️⃣ RAG INTEGRITY QA

Checks:

Correct chunk retrieval

Chunk relevance score

No cross-question contamination

No stale index usage

Rule

If retrieved chunk similarity < threshold → FAIL

4️⃣ LLM BEHAVIOR QA

Checks:

Is LLM generating or only classifying?

Is output deterministic?

Any creative language?

Any inferred content?

Rule

If output contains non-PDF facts → FAIL

5️⃣ EXAM FAIRNESS QA

Checks:

Equal difficulty distribution

No duplicate questions

Option balance (MCQs)

No pattern leakage

6️⃣ POST-EXAM ANSWER VALIDATION QA

Checks:

Answer correctness vs PDF

Explanation matches PDF

No paraphrase distortion

No missing steps

🧠 AGENT INPUT CONTRACT

This agent consumes artifacts, not vibes.

{
  "pdf_id": "pdf_103",
  "exam_id": "exam_552",
  "questions": [...],
  "answers": [...],
  "rag_chunks": [...],
  "llm_outputs": [...],
  "exam_mode": "pdf_extracted",
  "stage": "pre_publish"
}

🧪 AGENT OUTPUT (DECISION OBJECT)
{
  "verdict": "FAIL",
  "confidence": 0.91,
  "blocking": true,
  "reasons": [
    {
      "type": "ANSWER_LEAKAGE",
      "severity": "CRITICAL",
      "evidence": "Answer phrase appears in RAG chunk c_91"
    },
    {
      "type": "LOW_RAG_SIMILARITY",
      "severity": "HIGH",
      "question_id": 12,
      "score": 0.62
    }
  ],
  "recommendation": "Block exam publish until fixed"
}


This verdict is binding.
"""

class AntigravityQA:
    """
    Antigravity-QA Agent
    Role: System Guardian
    Responsibility: Adversarial Quality Assurance
    """
    
    @staticmethod
    def run_qa_check(input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs the adversarial QA check using the LLM.
        
        Args:
            input_data: The exam data to validate, matching the AGENT INPUT CONTRACT.
            
        Returns:
            Dict containing the verdict, confidence, blocking status, reasons, and recommendation.
        """
        
        # Construct the minimal prompt structure for LLMRunner
        # Pass the input data as the user message
        blueprint_prompt = {
            "system": ANTIGRAVITY_QA_SYSTEM_PROMPT,
            "user": json.dumps(input_data, indent=2)
        }
        
        # Configuration for the validation run
        batch_config = {
            "batch_id": f"QA_CHECK_{input_data.get('exam_id', 'unknown')}",
            "type": "validation",
            "count": 1
        }
        
        # Set strict parameters for the agent
        skill_metadata = {
            "skill_id": "antigravity_qa",
            "llm_params": {
                "temperature": 0.1,  # Low temp for deterministic checking
                "max_tokens": 4096   # Allow sufficient output for detailed reasons
            }
        }
        
        try:
            logger.info("Antigravity-QA: Initiating adversarial check...")
            
            # Using LLMRunner to execute the prompt
            result = LLMRunner.run_batch(blueprint_prompt, batch_config, skill_metadata)
            
            if not result:
                logger.error("Antigravity-QA: Failed to get response from LLM")
                return {
                    "verdict": "FAIL",
                    "confidence": 1.0,
                    "blocking": True,
                    "reasons": [{"type": "SYSTEM_ERROR", "severity": "CRITICAL", "evidence": "LLM returned no response"}],
                    "recommendation": "Block exam due to QA system failure"
                }

            logger.info(f"Antigravity-QA Verdict: {result.get('verdict')}")
            return result
            
        except Exception as e:
            logger.error(f"Antigravity-QA execution error: {e}")
            return {
                "verdict": "FAIL",
                "confidence": 1.0,
                "blocking": True,
                "reasons": [{"type": "EXCEPTION", "severity": "CRITICAL", "evidence": str(e)}],
                "recommendation": "Block exam due to QA exception"
            }
