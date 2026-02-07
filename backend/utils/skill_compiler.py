"""
Skill Compiler - Upskill Architecture Core Component

Replaces prompt engineering with deterministic skill compilation.
Loads skill definitions from SKILL.md files and compiles them with runtime variables.
"""

import os
import json
import re
import logging
from typing import Dict, Optional, Any
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Skill:
    """Represents a loaded skill definition"""
    skill_id: str
    version: str
    format_type: str
    template: str  # Raw SKILL.md content
    metadata: Dict[str, Any]  # Parsed skill_meta.json
    

@dataclass
class SkillPacket:
    """Compiled skill ready for LLM execution"""
    skill_id: str
    system_prompt: str  # Compiled prompt with variables substituted
    llm_params: Dict[str, Any]  # Temperature, max_tokens, etc.
    validation_schema: Dict[str, Any]  # JSON schema for output validation
    format_type: str


class SkillCompiler:
    """
    Compiles skills from definition files into executable prompts.
    
    This is the KEY component that replaces prompt engineering.
    """
    
    def __init__(self, skills_dir: str = None):
        """
        Initialize SkillCompiler
        
        Args:
            skills_dir: Path to skills directory (default: project_root/skills)
        """
        if skills_dir is None:
            # Auto-detect skills directory
            current_file = Path(__file__).resolve()
            # backend/utils/skill_compiler.py -> backend/utils -> backend -> project_root
            project_root = current_file.parent.parent.parent
            skills_dir = project_root / "skills"
        
        self.skills_dir = Path(skills_dir)
        self.skill_cache: Dict[str, Skill] = {}
        
        logger.info(f"SkillCompiler initialized with skills_dir: {self.skills_dir}")
        
        # Verify skills directory exists
        if not self.skills_dir.exists():
            logger.warning(f"Skills directory not found at {self.skills_dir}")
        
        # Pre-load all skills at startup
        self._preload_skills()
    
    def _preload_skills(self):
        """Pre-load all skills into cache at startup"""
        skill_names = ["mcq_generation", "short_answer_generation", "descriptive_generation"]
        
        for skill_name in skill_names:
            try:
                self.load_skill(skill_name)
                logger.info(f"Pre-loaded skill: {skill_name}")
            except Exception as e:
                logger.error(f"Failed to pre-load skill {skill_name}: {e}")
    
    def load_skill(self, skill_name: str) -> Skill:
        """
        Load a skill from the filesystem
        
        Args:
            skill_name: Name of skill directory (e.g., "mcq_generation")
            
        Returns:
            Loaded Skill object
            
        Raises:
            FileNotFoundError: If skill files don't exist
            ValueError: If skill files are malformed
        """
        # Check cache first
        if skill_name in self.skill_cache:
            return self.skill_cache[skill_name]
        
        skill_path = self.skills_dir / skill_name
        skill_md_path = skill_path / "SKILL.md"
        skill_meta_path = skill_path / "skill_meta.json"
        
        # Validate files exist
        if not skill_md_path.exists():
            raise FileNotFoundError(f"SKILL.md not found at {skill_md_path}")
        if not skill_meta_path.exists():
            raise FileNotFoundError(f"skill_meta.json not found at {skill_meta_path}")
        
        # Load SKILL.md template
        with open(skill_md_path, 'r', encoding='utf-8') as f:
            template = f.read()
        
        # Load skill_meta.json
        with open(skill_meta_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # Validate metadata
        required_fields = ["skill_id", "version", "format_type", "llm_params"]
        for field in required_fields:
            if field not in metadata:
                raise ValueError(f"skill_meta.json missing required field: {field}")
        
        # Create Skill object
        skill = Skill(
            skill_id=metadata["skill_id"],
            version=metadata["version"],
            format_type=metadata["format_type"],
            template=template,
            metadata=metadata
        )
        
        # Cache it
        self.skill_cache[skill_name] = skill
        
        logger.info(f"Loaded skill: {skill.skill_id} v{skill.version}")
        return skill
    
    def compile_skill(self, skill_name: str, variables: Dict[str, Any]) -> SkillPacket:
        """
        Compile a skill with runtime variables
        
        Args:
            skill_name: Name of skill to compile
            variables: Dict with keys: count, topic, difficulty, context
            
        Returns:
            SkillPacket ready for LLM execution
            
        Example:
            packet = compiler.compile_skill("mcq_generation", {
                "count": 5,
                "topic": "AI Ethics",
                "difficulty": "medium",
                "context": "RAG retrieved text..."
            })
        """
        # Load skill
        skill = self.load_skill(skill_name)
        
        # Validate required variables
        required_vars = ["count", "topic", "difficulty", "context"]
        for var in required_vars:
            if var not in variables:
                raise ValueError(f"Missing required variable: {var}")
        
        # Substitute template variables
        compiled_prompt = self._substitute_variables(skill.template, variables)
        
        # Create SkillPacket
        packet = SkillPacket(
            skill_id=skill.skill_id,
            system_prompt=compiled_prompt,
            llm_params=skill.metadata.get("llm_params", {}),
            validation_schema=skill.metadata.get("validation_schema", {}),
            format_type=skill.format_type
        )
        
        logger.info(f"Compiled skill: {skill.skill_id} with {len(compiled_prompt)} chars")
        return packet
    
    def _substitute_variables(self, template: str, variables: Dict[str, Any]) -> str:
        """
        Substitute {{variable}} placeholders in template
        
        Args:
            template: Template string with {{var}} placeholders
            variables: Dict of variable values
            
        Returns:
            Template with variables substituted
        """
        result = template
        
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"  # {{key}}
            result = result.replace(placeholder, str(value))
        
        # Check for unsubstituted variables (indicates missing variable)
        unsubstituted = re.findall(r'\{\{(\w+)\}\}', result)
        if unsubstituted:
            logger.warning(f"Unsubstituted variables in template: {unsubstituted}")
        
        return result
    
    def get_skill_metadata(self, skill_name: str) -> Dict[str, Any]:
        """
        Get metadata for a skill without compiling
        
        Args:
            skill_name: Name of skill
            
        Returns:
            Skill metadata dict
        """
        skill = self.load_skill(skill_name)
        return skill.metadata
    
    def get_rag_chunks_count(self, skill_name: str) -> int:
        """
        Get recommended RAG chunk count for a skill
        
        Args:
            skill_name: Name of skill
            
        Returns:
            Number of RAG chunks to retrieve
        """
        metadata = self.get_skill_metadata(skill_name)
        return metadata.get("rag_chunks", 2)
    
    def get_batch_size_limits(self, skill_name: str) -> tuple[int, int]:
        """
        Get min/max batch size for a skill
        
        Args:
            skill_name: Name of skill
            
        Returns:
            Tuple of (min_batch_size, max_batch_size)
        """
        metadata = self.get_skill_metadata(skill_name)
        return (
            metadata.get("min_batch_size", 1),
            metadata.get("max_batch_size", 5)
        )
    
    def validate_skill(self, skill_name: str) -> bool:
        """
        Validate that a skill is properly configured
        
        Args:
            skill_name: Name of skill to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            skill = self.load_skill(skill_name)
            
            # Check template has required placeholders
            required_placeholders = ["{{count}}", "{{topic}}", "{{difficulty}}", "{{context}}"]
            for placeholder in required_placeholders:
                if placeholder not in skill.template:
                    logger.error(f"Skill {skill_name} missing placeholder: {placeholder}")
                    return False
            
            # Check metadata has required fields
            required_fields = ["skill_id", "version", "format_type", "llm_params"]
            for field in required_fields:
                if field not in skill.metadata:
                    logger.error(f"Skill {skill_name} missing metadata field: {field}")
                    return False
            
            logger.info(f"Skill {skill_name} validation: PASSED")
            return True
            
        except Exception as e:
            logger.error(f"Skill {skill_name} validation failed: {e}")
            return False
    
    def list_available_skills(self) -> list[str]:
        """
        List all available skill names
        
        Returns:
            List of skill directory names
        """
        if not self.skills_dir.exists():
            return []
        
        skills = []
        for item in self.skills_dir.iterdir():
            if item.is_dir() and (item / "SKILL.md").exists():
                skills.append(item.name)
        
        return sorted(skills)


# Singleton instance for global use
_compiler_instance: Optional[SkillCompiler] = None


def get_skill_compiler() -> SkillCompiler:
    """
    Get singleton SkillCompiler instance
    
    Returns:
        Global SkillCompiler instance
    """
    global _compiler_instance
    if _compiler_instance is None:
        _compiler_instance = SkillCompiler()
    return _compiler_instance
