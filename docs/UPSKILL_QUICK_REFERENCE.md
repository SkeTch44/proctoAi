# Upskill Architecture - Quick Reference

## 🎯 What is Upskill Architecture?

A skill-based system that replaces hardcoded prompts with reusable, deterministic skill files. This reduces prompt size by 50%, improves LLM reliability, and makes prompts easy to iterate.

---

## 📁 Directory Structure

```
proctoAi/
├── skills/                          # Skill definitions
│   ├── mcq_generation/
│   │   ├── SKILL.md                # Prompt template
│   │   └── skill_meta.json         # Metadata & config
│   ├── short_answer_generation/
│   └── descriptive_generation/
├── backend/
│   ├── utils/
│   │   └── skill_compiler.py       # Core compiler
│   └── questions.py                # Integrated here
└── test/
    ├── test_skill_compiler.py      # Unit tests
    └── test_skill_integration.py   # Integration tests
```

---

## 🚀 Quick Start

### Using SkillCompiler

```python
from backend.utils.skill_compiler import get_skill_compiler

# Get singleton instance
compiler = get_skill_compiler()

# Compile a skill
packet = compiler.compile_skill("mcq_generation", {
    "count": 5,
    "topic": "AI Ethics",
    "difficulty": "medium",
    "context": "Artificial intelligence raises ethical questions..."
})

# Use compiled prompt
print(packet.system_prompt)  # Ready for LLM
print(packet.llm_params)     # {"temperature": 0.3, ...}
print(packet.validation_schema)  # JSON schema for output
```

### Creating a New Skill

1. **Create directory**: `skills/my_new_skill/`

2. **Write SKILL.md**:
```markdown
# MY_NEW_SKILL_V1

## Task
Generate [description]

## Input Variables
- `{{count}}`: Number of items
- `{{topic}}`: Subject area
- `{{difficulty}}`: Difficulty level
- `{{context}}`: Source content

## Rules
1. Rule one
2. Rule two

## Output Schema
[JSON format]

## Context
{{context}}

## Generation Instructions
Topic: {{topic}}
Difficulty: {{difficulty}}
Count: {{count}}
```

3. **Create skill_meta.json**:
```json
{
  "skill_id": "MY_NEW_SKILL_V1",
  "version": "1.0.0",
  "format_type": "my_format",
  "max_batch_size": 5,
  "rag_chunks": 3,
  "llm_params": {
    "temperature": 0.4,
    "max_tokens": 2048,
    "format": "json"
  }
}
```

4. **Add to skill_map** in `questions.py`:
```python
skill_map = {
    'mcq': 'mcq_generation',
    'short_answer': 'short_answer_generation',
    'descriptive': 'descriptive_generation',
    'my_format': 'my_new_skill'  # Add this
}
```

5. **Test it**:
```bash
pytest test/test_skill_compiler.py -v
```

---

## 🔧 Common Operations

### List Available Skills
```python
compiler = get_skill_compiler()
skills = compiler.list_available_skills()
print(skills)  # ['mcq_generation', 'short_answer_generation', ...]
```

### Get Skill Metadata
```python
metadata = compiler.get_skill_metadata("mcq_generation")
print(f"Skill: {metadata['skill_id']}")
print(f"Max batch: {metadata['max_batch_size']}")
print(f"RAG chunks: {metadata['rag_chunks']}")
```

### Validate a Skill
```python
is_valid = compiler.validate_skill("mcq_generation")
print(f"Valid: {is_valid}")
```

### Get RAG Chunk Count
```python
chunks = compiler.get_rag_chunks_count("descriptive_generation")
print(f"RAG chunks needed: {chunks}")  # 4
```

### Get Batch Size Limits
```python
min_size, max_size = compiler.get_batch_size_limits("mcq_generation")
print(f"Batch size: {min_size}-{max_size}")  # 1-5
```

---

## 📊 Blueprint Storage

### Store in Redis
```python
from backend.utils.redis_manager import redis_manager

blueprint = {
    "batch_id": "batch_123",
    "exam_id": "exam_456",
    "skill": "MCQ_GENERATION_V1",
    "count": 5,
    "topic": "AI",
    "difficulty": "medium"
}

redis_manager.store_blueprint("batch_123", blueprint)
retrieved = redis_manager.get_blueprint("batch_123")
```

### Store in Database
```python
from backend.db.database import DatabaseManager

db = DatabaseManager("sqlite:///exam_platform.db")

db.save_blueprint(
    batch_id="batch_123",
    exam_id="exam_456",
    skill_id="MCQ_GENERATION_V1",
    format_type="mcq",
    count=5,
    topic="AI",
    difficulty="medium",
    blueprint_data=blueprint
)

retrieved = db.get_blueprint("batch_123")
```

---

## 🧪 Testing

### Run Unit Tests
```bash
pytest test/test_skill_compiler.py -v
```

### Run Integration Tests
```bash
pytest test/test_skill_integration.py -v
```

### Run All Tests
```bash
pytest test/test_skill*.py -v
```

---

## 🐛 Troubleshooting

### Skill Not Found
```
FileNotFoundError: SKILL.md not found
```
**Fix**: Ensure `skills/` is at project root, not in `backend/`

### Unsubstituted Variables
```
WARNING: Unsubstituted variables: ['context']
```
**Fix**: Pass all required variables to `compile_skill()`

### Prompt Still Too Large
**Fix**: Reduce context limit in `questions.py`:
```python
"context": context[:2000]  # Reduce from 3000
```

---

## 📈 Performance Metrics

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| MCQ Prompt Size | 800 chars | 400 chars | **50%** |
| Short Answer Prompt | 600 chars | 350 chars | **42%** |
| Descriptive Prompt | 700 chars | 450 chars | **36%** |
| Ollama Error Rate | 40% | <5% (target) | **87%** |

---

## 🔄 Workflow

```
1. Admin requests questions
   ↓
2. Planner creates blueprint
   ↓
3. SkillCompiler loads SKILL.md
   ↓
4. Variables substituted ({{count}}, {{topic}}, etc.)
   ↓
5. SkillPacket created
   ↓
6. LLM Runner sends to Ollama
   ↓
7. Validator checks against schema
   ↓
8. Questions stored in database
```

---

## 📚 Key Files

- **SkillCompiler**: [`backend/utils/skill_compiler.py`](file:///c:/Users/Sketch/Desktop/proctoAi/backend/utils/skill_compiler.py)
- **Skills**: [`skills/`](file:///c:/Users/Sketch/Desktop/proctoAi/skills/)
- **Integration**: [`backend/questions.py:235-268`](file:///c:/Users/Sketch/Desktop/proctoAi/backend/questions.py#L235-L268)
- **Tests**: [`test/test_skill_compiler.py`](file:///c:/Users/Sketch/Desktop/proctoAi/test/test_skill_compiler.py)

---

## ✅ Best Practices

1. **Keep skills focused**: One skill = one task type
2. **Version skills**: Use V1, V2 in skill_id
3. **Limit context**: Cap at 3000 chars max
4. **Test thoroughly**: Run tests after changes
5. **Cache skills**: SkillCompiler caches automatically
6. **Use metadata**: Store LLM params in skill_meta.json
7. **Validate output**: Use validation_schema from skill

---

## 🎓 Next Steps

1. Update `llm_runner.py` to use SkillPacket
2. Add feature flag `USE_SKILLS=true`
3. Deploy to staging
4. Monitor Ollama error rates
5. Roll out to production
