# MCQ_GENERATION_V1

## Skill Metadata
- **Skill ID**: MCQ_GENERATION_V1
- **Version**: 1.0.0
- **Format**: Multiple Choice Questions
- **Batch Size**: 1-5 questions per call

## Task
Generate multiple-choice exam questions with exactly 4 options and 1 correct answer.

## Input Variables
- `{{count}}`: Number of questions to generate (1-5)
- `{{difficulty}}`: Difficulty level (easy, medium, hard, expert)
- `{{topic}}`: Subject or topic area
- `{{context}}`: Source content from RAG retrieval or document

## Rules
1. Generate EXACTLY `{{count}}` questions
2. Each question must be ONE clear sentence
3. Provide exactly 4 options labeled A, B, C, D
4. Only ONE option must be correct
5. All options must be plausible but distinct
6. Questions must be answerable from the context
7. Difficulty level: `{{difficulty}}`
8. Topic focus: `{{topic}}`

## Constraints
- NO markdown formatting
- NO explanations or rationale
- NO extra text outside JSON
- NO multi-part questions
- NO "all of the above" or "none of the above" options

## Output Schema
Return ONLY valid JSON array:
```json
[
  {
    "question": "Clear question text?",
    "options": {
      "A": "First option",
      "B": "Second option",
      "C": "Third option",
      "D": "Fourth option"
    },
    "answer": "A"
  }
]
```

## Validation Rules
- `question`: Non-empty string, 10-200 characters
- `options`: Object with exactly keys A, B, C, D
- `answer`: Single letter A, B, C, or D
- Array length must equal `{{count}}`

## Failure Handling
If context is insufficient or unclear:
- Return fewer questions rather than malformed output
- Ensure all returned questions are valid
- Do not hallucinate information not in context

## Context
{{context}}

## Generation Instructions
Topic: {{topic}}
Difficulty: {{difficulty}}
Count: {{count}}

Generate the questions now.
