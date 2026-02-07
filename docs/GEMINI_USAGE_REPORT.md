# Gemini Usage Report

## Executive Summary
The **Gemini AI** integration is currently **OPTIONAL but RECOMMENDED**. 

The core system (Exam taking, Proctoring, Grading) functions fully **without** Gemini. Gemini is only used to enhance the **Question Generation** feature with AI capabilities. Without Gemini, the system falls back to simple sentence extraction.

## Component Analysis

| Component | File Path | Usage Status | Dependency Type |
|-----------|-----------|--------------|-----------------|
| **Question Generator** | `backend/questions.py` | **ACTIVE** | **High** (Falls back to basic mode without it) |
| **Grading Engine** | `backend/grading.py` | **NONE** | None (Uses local `sentence-transformers`) |
| **Template Generator** | `backend/enhanced_question.py`| **NONE** | None (Rule-based templates) |
| **Proctoring** | `backend/models/cheat_detector.py` | **NONE** | None (Uses `OpenCV`, `MediaPipe`) |

## Detailed Breakdown

### 1. Question Generator (`backend/questions.py`)
- **Purpose**: Generates high-quality exam questions (MCQ, Essay, Case Study) from uploaded documents (PDF/DOCX) using RAG (Retrieval Augmented Generation).
- **Gemini Role**: 
    - Analyzes document context.
    - Creates semantic questions based on Bloom's Taxonomy.
    - Generates distractors for MCQs.
- **Without Gemini**: The system uses a **Fallback Mode** that extracts random sentences and converts them into simple "fill-in-the-blank" style MCQs. These are functional but low quality.

### 2. Grading Engine (`backend/grading.py`)
- **Purpose**: Auto-grades student answers, including essays and short answers.
- **Gemini Role**: **None**.
- **Implementation**: It uses a **local** model (`all-MiniLM-L6-v2` via `sentence-transformers`) to calculate semantic similarity. It does *not* send student data to Google.

### 3. Configuration (`backend/config.py`)
- Defines `GEMINI_API_KEY` which is loaded from the `.env` file.
- Currently configured to use **`gemini-2.0-flash`** (as verified in testing).

## Recommendation

To maintain a "Production Ready" quality:
1. **Keep Gemini Enabled**: The fallback question generator is too primitive for real-world usage.
2. **Monitor Quotas**: Your current API key is hitting **Rate Limits (HTTP 429)**. You must resolve the quota issue in [Google AI Studio](https://aistudio.google.com/) for reliable operation.
3. **Alternative**: If you cannot use Gemini, you must rely on the manual `Question Bank` or the `Template Generator` (`enhanced_question.py`) which creates randomized questions from pre-defined logic.
