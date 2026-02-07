# SHORT_ANSWER_GENERATION_V1

## Skill Metadata
- **Skill ID**: SHORT_ANSWER_GENERATION_V1
- **Version**: 1.0.0
- **Format**: Short Answer Questions
- **Batch Size**: 1-5 questions per call

## Task
Generate short-answer exam questions that require 1-3 sentence responses.

## Input Variables
- `{{count}}`: Number of questions to generate (1-5)
- `{{difficulty}}`: Difficulty level (easy, medium, hard, expert)
- `{{topic}}`: Subject or topic area
- `{{context}}`: Source content from RAG retrieval or document

## Rules
1. Generate EXACTLY `{{count}}` questions
2. Each question must test a specific concept
3. Expected answer length: 1-3 sentences
4. Questions must be answerable from context
5. Avoid vague or opinion-based questions
6. Provide expected answer for grading reference
7. Difficulty level: `{{difficulty}}`
8. Topic focus: `{{topic}}`

## Constraints
- NO multi-part questions
- NO yes/no questions
- NO explanations outside the expected_answer field
- NO markdown formatting
- NO extra text outside JSON

## Output Schema
Return ONLY valid JSON array:
```json
[
  {
    "question": "Specific question text?",
    "expected_answer": "Model answer in 1-3 sentences"
  }
]
```

## Validation Rules
- `question`: Non-empty string, 15-250 characters
- `expected_answer`: Non-empty string, 20-500 characters
- Array length must equal `{{count}}`

## Failure Handling
If context is insufficient:
- Return fewer questions rather than malformed output
- Ensure expected answers are grounded in context
- Do not generate questions that cannot be answered from context

## Context
{{context}}

## Generation Instructions
Topic: {{topic}}
Difficulty: {{difficulty}}
Count: {{count}}

Generate the questions now.
