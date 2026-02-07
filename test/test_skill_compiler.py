"""
Unit tests for SkillCompiler (Upskill Architecture)

Tests skill loading, compilation, validation, and error handling.
"""

import pytest
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.utils.skill_compiler import SkillCompiler, Skill, SkillPacket


class TestSkillCompiler:
    """Test suite for SkillCompiler"""
    
    @pytest.fixture
    def compiler(self):
        """Create a SkillCompiler instance"""
        return SkillCompiler()
    
    def test_compiler_initialization(self, compiler):
        """Test that compiler initializes correctly"""
        assert compiler is not None
        assert compiler.skills_dir.exists()
        assert len(compiler.skill_cache) > 0  # Pre-loaded skills
    
    def test_load_mcq_skill(self, compiler):
        """Test loading MCQ generation skill"""
        skill = compiler.load_skill("mcq_generation")
        
        assert skill is not None
        assert skill.skill_id == "MCQ_GENERATION_V1"
        assert skill.version == "1.0.0"
        assert skill.format_type == "mcq"
        assert "{{count}}" in skill.template
        assert "{{topic}}" in skill.template
        assert "{{difficulty}}" in skill.template
        assert "{{context}}" in skill.template
    
    def test_load_short_answer_skill(self, compiler):
        """Test loading short answer generation skill"""
        skill = compiler.load_skill("short_answer_generation")
        
        assert skill is not None
        assert skill.skill_id == "SHORT_ANSWER_GENERATION_V1"
        assert skill.format_type == "short_answer"
    
    def test_load_descriptive_skill(self, compiler):
        """Test loading descriptive generation skill"""
        skill = compiler.load_skill("descriptive_generation")
        
        assert skill is not None
        assert skill.skill_id == "DESCRIPTIVE_GENERATION_V1"
        assert skill.format_type == "descriptive"
    
    def test_skill_caching(self, compiler):
        """Test that skills are cached after first load"""
        skill1 = compiler.load_skill("mcq_generation")
        skill2 = compiler.load_skill("mcq_generation")
        
        # Should return same object from cache
        assert skill1 is skill2
    
    def test_compile_mcq_skill(self, compiler):
        """Test compiling MCQ skill with variables"""
        packet = compiler.compile_skill("mcq_generation", {
            "count": 5,
            "topic": "AI Ethics",
            "difficulty": "medium",
            "context": "Artificial intelligence raises important ethical questions..."
        })
        
        assert isinstance(packet, SkillPacket)
        assert packet.skill_id == "MCQ_GENERATION_V1"
        assert packet.format_type == "mcq"
        assert "5" in packet.system_prompt  # Count substituted
        assert "AI Ethics" in packet.system_prompt  # Topic substituted
        assert "medium" in packet.system_prompt  # Difficulty substituted
        assert "{{count}}" not in packet.system_prompt  # No unsubstituted vars
        assert "{{topic}}" not in packet.system_prompt
    
    def test_compile_short_answer_skill(self, compiler):
        """Test compiling short answer skill"""
        packet = compiler.compile_skill("short_answer_generation", {
            "count": 3,
            "topic": "Machine Learning",
            "difficulty": "hard",
            "context": "Machine learning is a subset of AI..."
        })
        
        assert packet.skill_id == "SHORT_ANSWER_GENERATION_V1"
        assert packet.format_type == "short_answer"
        assert "3" in packet.system_prompt
        assert "Machine Learning" in packet.system_prompt
    
    def test_compile_descriptive_skill(self, compiler):
        """Test compiling descriptive skill"""
        packet = compiler.compile_skill("descriptive_generation", {
            "count": 1,
            "topic": "Neural Networks",
            "difficulty": "expert",
            "context": "Neural networks are computational models..."
        })
        
        assert packet.skill_id == "DESCRIPTIVE_GENERATION_V1"
        assert packet.format_type == "descriptive"
        assert "1" in packet.system_prompt
        assert "Neural Networks" in packet.system_prompt
    
    def test_compile_missing_variable(self, compiler):
        """Test that compilation fails with missing variables"""
        with pytest.raises(ValueError, match="Missing required variable"):
            compiler.compile_skill("mcq_generation", {
                "count": 5,
                "topic": "AI"
                # Missing difficulty and context
            })
    
    def test_load_nonexistent_skill(self, compiler):
        """Test loading a skill that doesn't exist"""
        with pytest.raises(FileNotFoundError):
            compiler.load_skill("nonexistent_skill")
    
    def test_get_skill_metadata(self, compiler):
        """Test retrieving skill metadata"""
        metadata = compiler.get_skill_metadata("mcq_generation")
        
        assert metadata["skill_id"] == "MCQ_GENERATION_V1"
        assert metadata["format_type"] == "mcq"
        assert "llm_params" in metadata
        assert "validation_schema" in metadata
    
    def test_get_rag_chunks_count(self, compiler):
        """Test getting RAG chunk count for skills"""
        mcq_chunks = compiler.get_rag_chunks_count("mcq_generation")
        short_chunks = compiler.get_rag_chunks_count("short_answer_generation")
        desc_chunks = compiler.get_rag_chunks_count("descriptive_generation")
        
        assert mcq_chunks == 2
        assert short_chunks == 3
        assert desc_chunks == 4
    
    def test_get_batch_size_limits(self, compiler):
        """Test getting batch size limits"""
        min_size, max_size = compiler.get_batch_size_limits("mcq_generation")
        
        assert min_size == 1
        assert max_size == 5
        
        min_desc, max_desc = compiler.get_batch_size_limits("descriptive_generation")
        assert max_desc == 2  # Descriptive has smaller batch size
    
    def test_validate_skill(self, compiler):
        """Test skill validation"""
        assert compiler.validate_skill("mcq_generation") == True
        assert compiler.validate_skill("short_answer_generation") == True
        assert compiler.validate_skill("descriptive_generation") == True
    
    def test_list_available_skills(self, compiler):
        """Test listing all available skills"""
        skills = compiler.list_available_skills()
        
        assert "mcq_generation" in skills
        assert "short_answer_generation" in skills
        assert "descriptive_generation" in skills
        assert len(skills) >= 3
    
    def test_llm_params_in_packet(self, compiler):
        """Test that LLM params are included in compiled packet"""
        packet = compiler.compile_skill("mcq_generation", {
            "count": 5,
            "topic": "Test",
            "difficulty": "easy",
            "context": "Test context"
        })
        
        assert "temperature" in packet.llm_params
        assert "max_tokens" in packet.llm_params
        assert packet.llm_params["temperature"] == 0.3
        assert packet.llm_params["format"] == "json"
    
    def test_validation_schema_in_packet(self, compiler):
        """Test that validation schema is included in packet"""
        packet = compiler.compile_skill("mcq_generation", {
            "count": 5,
            "topic": "Test",
            "difficulty": "easy",
            "context": "Test context"
        })
        
        assert packet.validation_schema is not None
        assert packet.validation_schema["type"] == "array"
        assert "items" in packet.validation_schema
    
    def test_prompt_size_reduction(self, compiler):
        """Test that skill compilation produces smaller prompts"""
        # Legacy prompt would be ~800+ characters
        # Skill-based should be more compact
        packet = compiler.compile_skill("mcq_generation", {
            "count": 5,
            "topic": "AI",
            "difficulty": "medium",
            "context": "Test context" * 50  # Large context
        })
        
        # Prompt should be reasonable size (skill template + context)
        # Not a strict assertion, just checking it's not absurdly large
        assert len(packet.system_prompt) < 5000  # Should be much smaller than old prompts


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
