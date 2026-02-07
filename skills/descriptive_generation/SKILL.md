# DESCRIPTIVE_GENERATION_V1

## Skill Metadata
- **Skill ID**: DESCRIPTIVE_GENERATION_V1
- **Version**: 1.0.0
- **Format**: Long Answer / Essay Questions
- **Batch Size**: 1-2 questions per call

## Task
Generate long-answer exam questions requiring detailed, structured responses.

## Input Variables
- `{{count}}`: Number of questions to generate (1-2)
- `{{difficulty}}`: Difficulty level (easy, medium, hard, expert)
- `{{topic}}`: Subject or topic area
- `{{context}}`: Source content from RAG retrieval or document

## Rules
1. Generate EXACTLY `{{count}}` questions
2. Questions must be specific and bounded
3. Avoid multi-part ambiguity
4. Provide answer outline with key points
5. Questions must require analytical thinking
6. Expected answer: 5-10 sentences or structured outline
7. Difficulty level: `{{difficulty}}`
8. Topic focus: `{{topic}}`

## Constraints
- NO vague or open-ended questions
- NO "discuss" or "explain everything" questions
- NO markdown formatting
- NO extra text outside JSON
- Questions must be answerable in exam context (30-45 minutes)

## Output Schema
Return ONLY valid JSON array:
```json
[
  {
    "question": "Specific analytical question?",
    "answer_outline": [
      "Key point 1",
      "Key point 2",
      "Key point 3",
      "Key point 4"
    ]
  }
]
```

## Validation Rules
- `question`: Non-empty string, 20-300 characters
- `answer_outline`: Array of 3-7 strings
- Each outline point: 10-200 characters
- Array length must equal `{{count}}`

## Failure Handling
If context is insufficient:
- Return fewer questions rather than malformed output
- Ensure questions are specific and bounded
- Provide clear answer outline for grading

## Context
{{context}}

## Generation Instructions
Topic: {{topic}}
Difficulty: {{difficulty}}
Count: {{count}}

Generate the questions now.
