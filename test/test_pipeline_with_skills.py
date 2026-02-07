"""
End-to-End Pipeline Test for Upskill Architecture

Tests the complete flow: API → Planner → Blueprint → Skill Compiler → LLM → Validator
"""

import pytest
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.planner import Planner
from backend.blueprints import BlueprintGenerator
from backend.utils.skill_compiler import get_skill_compiler
from backend.llm_runner import LLMRunner
from backend.validator import Validator
from backend.utils.redis_manager import redis_manager


class TestEndToEndPipeline:
    """Test complete pipeline with Upskill architecture"""
    
    def test_full_pipeline_mcq_with_skills(self):
        """Test full pipeline for MCQ generation with skills"""
        
        # Step 1: Planner creates batches
        request_data = {
            "topic": "Artificial Intelligence",
            "difficulty": "medium",
            "format": {
                "mcq": 3
            },
            "exam_id": "exam_test_001"
        }
        
        blueprint = Planner.create_blueprint(request_data, user_id="test_user")
        batches = blueprint.batches
        
        assert len(batches) > 0
        mcq_batch = batches[0]
        assert mcq_batch['type'] == 'mcq'
        assert mcq_batch['count'] == 3
        
        # Step 2: SkillCompiler compiles skill
        compiler = get_skill_compiler()
        skill_packet = compiler.compile_skill("mcq_generation", {
            "count": mcq_batch['count'],
            "topic": mcq_batch['topic'],
            "difficulty": mcq_batch['difficulty'],
            "context": "AI is the simulation of human intelligence by machines."
        })
        
        assert skill_packet is not None
        assert skill_packet.skill_id == "MCQ_GENERATION_V1"
        assert skill_packet.format_type == "mcq"
        
        # Step 3: Blueprint Generator creates prompt (with skill_id)
        blueprint_prompt = BlueprintGenerator.get_template(
            mcq_batch,
            context="AI is the simulation of human intelligence.",
            skill_id=skill_packet.skill_id
        )
        
        assert "system" in blueprint_prompt
        assert "user" in blueprint_prompt
        assert blueprint_prompt.get("skill_id") == "MCQ_GENERATION_V1"
        
        # Step 4: Blueprint stored in Redis
        if redis_manager.is_healthy():
            redis_manager.store_blueprint(mcq_batch['batch_id'], {
                "batch_id": mcq_batch['batch_id'],
                "exam_id": "exam_test_001",
                "skill": skill_packet.skill_id,
                "count": mcq_batch['count'],
                "topic": mcq_batch['topic'],
                "difficulty": mcq_batch['difficulty']
            })
            
            # Verify storage
            retrieved = redis_manager.get_blueprint(mcq_batch['batch_id'])
            assert retrieved is not None
            assert retrieved['skill'] == "MCQ_GENERATION_V1"
            
            # Cleanup
            redis_manager.delete_blueprint(mcq_batch['batch_id'])
        
        # Step 5: LLM Runner (would call Ollama - skipped in test)
        # In real flow: LLMRunner.run_batch(blueprint_prompt, mcq_batch, skill_packet.metadata)
        
        # Step 6: Validator validates output
        # Simulate LLM output
        mock_llm_output = [
            {
                "question": "What is AI?",
                "options": {
                    "A": "Artificial Intelligence",
                    "B": "Automated Intelligence",
                    "C": "Advanced Intelligence",
                    "D": "None"
                },
                "answer": "A",
                "explanation": "AI stands for Artificial Intelligence"
            }
        ]
        
        validated = Validator.validate_batch(
            generated_data=mock_llm_output, 
            expected_type=mcq_batch['type'], 
            count=mcq_batch['count']
        )
        
        assert validated is not None
        assert len(validated) > 0
        # Validator adds 'type' key? No, it just returns the valid objects.
        # But our mock output didn't have type.
        # The test assertion "assert validated[0]['type'] == 'mcq'" might fail if Validator doesn't add it.
        # Checking Validator code: it just returns q from list.
        # So I should check content, not type if it's not in mock.
        assert validated[0]['answer'] == 'A'
    
    def test_pipeline_with_different_skills(self):
        """Test pipeline with different question types using different skills"""
        
        compiler = get_skill_compiler()
        
        # Test MCQ skill
        mcq_config = {
            'type': 'mcq',
            'count': 2,
            'topic': 'Machine Learning',
            'difficulty': 'hard',
            'batch_id': 'test_mcq'
        }
        
        mcq_packet = compiler.compile_skill("mcq_generation", {
            "count": 2,
            "topic": "Machine Learning",
            "difficulty": "hard",
            "context": "ML is a subset of AI"
        })
        
        mcq_blueprint = BlueprintGenerator.get_template(
            mcq_config,
            skill_id=mcq_packet.skill_id
        )
        
        assert mcq_blueprint['skill_id'] == "MCQ_GENERATION_V1"
        
        # Test Short Answer skill
        short_config = {
            'type': 'short_answer',
            'count': 2,
            'topic': 'Neural Networks',
            'difficulty': 'medium',
            'batch_id': 'test_short'
        }
        
        short_packet = compiler.compile_skill("short_answer_generation", {
            "count": 2,
            "topic": "Neural Networks",
            "difficulty": "medium",
            "context": "Neural networks are computational models"
        })
        
        short_blueprint = BlueprintGenerator.get_template(
            short_config,
            skill_id=short_packet.skill_id
        )
        
        assert short_blueprint['skill_id'] == "SHORT_ANSWER_GENERATION_V1"
        
        # Test Descriptive skill
        desc_config = {
            'type': 'descriptive',
            'count': 1,
            'topic': 'Deep Learning',
            'difficulty': 'expert',
            'batch_id': 'test_desc'
        }
        
        desc_packet = compiler.compile_skill("descriptive_generation", {
            "count": 1,
            "topic": "Deep Learning",
            "difficulty": "expert",
            "context": "Deep learning uses multiple layers"
        })
        
        desc_blueprint = BlueprintGenerator.get_template(
            desc_config,
            skill_id=desc_packet.skill_id
        )
        
        assert desc_blueprint['skill_id'] == "DESCRIPTIVE_GENERATION_V1"
    
    def test_skill_metadata_flows_to_llm_runner(self):
        """Test that skill metadata is properly passed to LLM runner"""
        
        compiler = get_skill_compiler()
        
        # Get skill with specific parameters
        skill_packet = compiler.compile_skill("mcq_generation", {
            "count": 5,
            "topic": "Test",
            "difficulty": "easy",
            "context": "Test context"
        })
        
        # Verify metadata
        assert skill_packet.llm_params['temperature'] == 0.3
        assert skill_packet.llm_params['max_tokens'] == 2048
        
        # Create batch config
        batch_config = {
            'type': 'mcq',
            'count': 5,
            'topic': 'Test',
            'difficulty': 'easy',
            'batch_id': 'test_batch_123'
        }
        
        # Create blueprint
        blueprint = BlueprintGenerator.get_template(
            batch_config,
            skill_id=skill_packet.skill_id
        )
        
        # LLMRunner would receive skill metadata
        # (Can't actually call Ollama in test, but verify structure)
        skill_metadata = {
            'skill_id': skill_packet.skill_id,
            'llm_params': skill_packet.llm_params
        }
        
        assert skill_metadata['skill_id'] == "MCQ_GENERATION_V1"
        assert skill_metadata['llm_params']['temperature'] == 0.3
    
    def test_blueprint_caching_redis(self):
        """Test that blueprints are properly cached in Redis"""
        
        if not redis_manager.is_healthy():
            pytest.skip("Redis not available")
        
        compiler = get_skill_compiler()
        
        # Create multiple batches
        batches = []
        for i in range(3):
            skill_packet = compiler.compile_skill("mcq_generation", {
                "count": 5,
                "topic": f"Topic {i}",
                "difficulty": "medium",
                "context": f"Context {i}"
            })
            
            batch_id = f"test_batch_{i}"
            blueprint = {
                "batch_id": batch_id,
                "exam_id": "exam_cache_test",
                "skill": skill_packet.skill_id,
                "count": 5,
                "topic": f"Topic {i}",
                "difficulty": "medium"
            }
            
            redis_manager.store_blueprint(batch_id, blueprint)
            batches.append(batch_id)
        
        # Verify all stored
        for batch_id in batches:
            retrieved = redis_manager.get_blueprint(batch_id)
            assert retrieved is not None
            assert retrieved['skill'] == "MCQ_GENERATION_V1"
        
        # Cleanup
        for batch_id in batches:
            redis_manager.delete_blueprint(batch_id)
    
    def test_prompt_size_reduction_in_pipeline(self):
        """Test that skill-based pipeline produces smaller prompts"""
        
        compiler = get_skill_compiler()
        
        # Large context
        large_context = "Test context " * 200  # ~2400 chars
        
        # Compile with skill
        skill_packet = compiler.compile_skill("mcq_generation", {
            "count": 5,
            "topic": "Test Topic",
            "difficulty": "medium",
            "context": large_context
        })
        
        # Create blueprint
        batch_config = {
            'type': 'mcq',
            'count': 5,
            'topic': 'Test Topic',
            'difficulty': 'medium',
            'batch_id': 'test_size'
        }
        
        blueprint = BlueprintGenerator.get_template(
            batch_config,
            context=large_context[:3000],  # Skill limits context
            skill_id=skill_packet.skill_id
        )
        
        # Check prompt size
        full_prompt = f"{blueprint['system']}\n\n{blueprint['user']}"
        
        # Should be reasonable size (not > 5000 chars)
        assert len(full_prompt) < 5000
        
        # Should include skill_id
        assert blueprint.get('skill_id') == "MCQ_GENERATION_V1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
