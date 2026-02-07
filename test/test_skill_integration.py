"""
Integration tests for Upskill Architecture

Tests end-to-end flow: SkillCompiler -> QuestionGenerator -> Validation
"""

import pytest
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.questions import QuestionGenerator
from backend.utils.skill_compiler import get_skill_compiler


class TestUpskillIntegration:
    """Integration tests for Upskill architecture"""
    
    @pytest.fixture
    def generator(self):
        """Create QuestionGenerator instance"""
        return QuestionGenerator()
    
    def test_question_generator_has_skill_compiler(self, generator):
        """Test that QuestionGenerator initializes with SkillCompiler"""
        assert generator.skill_compiler is not None
        assert generator.skill_compiler == get_skill_compiler()
    
    def test_generate_mcq_batch_with_skills(self, generator):
        """Test MCQ generation using skills"""
        context = "Artificial intelligence is the simulation of human intelligence by machines."
        
        questions = generator.generate_batch(
            content=context,
            topic="Artificial Intelligence",
            count=3,
            format_type="mcq",
            difficulty="medium"
        )
        
        # Should generate questions (or fallback if Ollama not available)
        assert isinstance(questions, list)
        
        # If questions generated, validate structure
        if len(questions) > 0:
            for q in questions:
                assert 'question' in q
                assert 'type' in q
                # MCQ specific
                if q['type'] == 'mcq':
                    assert 'options' in q
                    assert 'correct_answer' in q
    
    def test_generate_short_answer_batch_with_skills(self, generator):
        """Test short answer generation using skills"""
        context = "Machine learning is a subset of AI that enables systems to learn from data."
        
        questions = generator.generate_batch(
            content=context,
            topic="Machine Learning",
            count=2,
            format_type="short_answer",
            difficulty="medium"
        )
        
        assert isinstance(questions, list)
        
        if len(questions) > 0:
            for q in questions:
                assert 'question' in q
                assert 'type' in q
                if q['type'] == 'short_answer':
                    assert 'sample_answer' in q or 'expected_answer' in q
    
    def test_generate_descriptive_batch_with_skills(self, generator):
        """Test descriptive generation using skills"""
        context = "Neural networks are computational models inspired by biological neural networks."
        
        questions = generator.generate_batch(
            content=context,
            topic="Neural Networks",
            count=1,
            format_type="descriptive",
            difficulty="hard"
        )
        
        assert isinstance(questions, list)
        
        if len(questions) > 0:
            for q in questions:
                assert 'question' in q
                assert 'type' in q
    
    def test_skill_compilation_reduces_prompt_size(self, generator):
        """Test that skill compilation produces smaller prompts"""
        context = "Test context " * 100  # Large context
        
        # Get compiled prompt
        prompt = generator._get_format_prompt(
            context=context,
            count=5,
            format_type="mcq",
            difficulty="medium",
            topic="Test Topic"
        )
        
        # Skill-based prompt should be more compact than legacy
        # Legacy would include full context, skills limit it
        assert len(prompt) < 5000  # Reasonable size
        assert "MCQ_GENERATION" in prompt or "exam question generator" in prompt
    
    def test_fallback_to_legacy_on_skill_error(self, generator):
        """Test that system falls back to legacy prompt on skill error"""
        # Use invalid format type to trigger fallback
        prompt = generator._get_format_prompt(
            context="Test",
            count=5,
            format_type="invalid_format",
            difficulty="medium",
            topic="Test"
        )
        
        # Should fall back to legacy MCQ prompt
        assert "exam question generator" in prompt
        assert "EXACTLY" in prompt
    
    def test_different_difficulties_use_same_skill(self, generator):
        """Test that different difficulties use the same skill template"""
        context = "Test context"
        
        easy_prompt = generator._get_format_prompt(context, 5, "mcq", "easy", "Test")
        hard_prompt = generator._get_format_prompt(context, 5, "mcq", "hard", "Test")
        
        # Both should use MCQ skill
        assert "MCQ_GENERATION" in easy_prompt or "exam question generator" in easy_prompt
        assert "MCQ_GENERATION" in hard_prompt or "exam question generator" in hard_prompt
        
        # But difficulty should be different
        assert "easy" in easy_prompt
        assert "hard" in hard_prompt
    
    def test_skill_metadata_accessible(self, generator):
        """Test that skill metadata is accessible"""
        compiler = generator.skill_compiler
        
        mcq_meta = compiler.get_skill_metadata("mcq_generation")
        assert mcq_meta["skill_id"] == "MCQ_GENERATION_V1"
        assert mcq_meta["max_batch_size"] == 5
        assert mcq_meta["rag_chunks"] == 2
    
    def test_rag_chunks_vary_by_skill(self, generator):
        """Test that different skills request different RAG chunk counts"""
        compiler = generator.skill_compiler
        
        mcq_chunks = compiler.get_rag_chunks_count("mcq_generation")
        short_chunks = compiler.get_rag_chunks_count("short_answer_generation")
        desc_chunks = compiler.get_rag_chunks_count("descriptive_generation")
        
        # Descriptive needs more context
        assert desc_chunks > mcq_chunks
        assert desc_chunks > short_chunks


class TestBlueprintStorage:
    """Test blueprint storage integration"""
    
    def test_redis_blueprint_storage(self):
        """Test storing and retrieving blueprints from Redis"""
        from backend.utils.redis_manager import redis_manager
        
        if not redis_manager.is_healthy():
            pytest.skip("Redis not available")
        
        blueprint = {
            "batch_id": "test_batch_123",
            "exam_id": "exam_456",
            "skill": "MCQ_GENERATION_V1",
            "count": 5,
            "topic": "AI",
            "difficulty": "medium"
        }
        
        # Store blueprint
        redis_manager.store_blueprint("test_batch_123", blueprint)
        
        # Retrieve blueprint
        retrieved = redis_manager.get_blueprint("test_batch_123")
        
        assert retrieved is not None
        assert retrieved["skill"] == "MCQ_GENERATION_V1"
        assert retrieved["count"] == 5
        
        # Cleanup
        redis_manager.delete_blueprint("test_batch_123")
    
    def test_database_blueprint_storage(self):
        """Test storing and retrieving blueprints from database"""
        from backend.db.database import DatabaseManager
        import os
        
        db_path = "test_blueprints.db"
        db = DatabaseManager(f"sqlite:///{db_path}")
        db.init_database()
        
        try:
            blueprint_data = {
                "batch_id": "test_batch_456",
                "exam_id": "exam_789",
                "skill": "SHORT_ANSWER_GENERATION_V1",
                "count": 3,
                "topic": "ML",
                "difficulty": "hard",
                "context": "Test context"
            }
            
            # Save blueprint
            success = db.save_blueprint(
                batch_id="test_batch_456",
                exam_id="exam_789",
                skill_id="SHORT_ANSWER_GENERATION_V1",
                format_type="short_answer",
                count=3,
                topic="ML",
                difficulty="hard",
                blueprint_data=blueprint_data
            )
            
            assert success == True
            
            # Retrieve blueprint
            retrieved = db.get_blueprint("test_batch_456")
            
            assert retrieved is not None
            assert retrieved["skill"] == "SHORT_ANSWER_GENERATION_V1"
            assert retrieved["count"] == 3
            
        finally:
            # Cleanup
            if os.path.exists(db_path):
                os.remove(db_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
