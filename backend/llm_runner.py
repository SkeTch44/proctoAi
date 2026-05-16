import json
import logging
import re
from typing import Dict, Any, Optional
from backend.providers.llm_provider import get_llm_client

logger = logging.getLogger(__name__)

class LLMRunner:
    """
    Phase 4: LLM Runner
    Responsibility: Execute Blueprint against Model (Ollama/LLaMA)
    - Sync/Async HTTP call handling
    - Timeout management
    - JSON parsing (Strict)
    - Skill-aware parameter application (Upskill Architecture)
    """
    
    @staticmethod
    def run_batch(blueprint_prompt: Dict, batch_config: Dict, skill_metadata: Optional[Dict] = None) -> Optional[Any]:
        """
        Executes the prompt against the configured LLM via the provider abstraction.
        
        Args:
            blueprint_prompt: Dict with 'system' and 'user' prompts
            batch_config: Batch configuration with type, count, etc.
            skill_metadata: Optional skill metadata with LLM params (Upskill)
            
        Returns:
            Parsed JSON or None on failure.
        """
        
        # Determine strictness parameters based on type
        fmt = batch_config['type']
        
        # [UPSKILL] Extract skill-specific parameters if available
        if skill_metadata and 'llm_params' in skill_metadata:
            llm_params = skill_metadata['llm_params']
            temperature = llm_params.get('temperature', 0.7)
            max_tokens = llm_params.get('max_tokens', 2048)
            skill_id = skill_metadata.get('skill_id', 'UNKNOWN')
            logger.info(f"Using skill parameters from {skill_id}: temp={temperature}, max_tokens={max_tokens}")
        else:
            # Legacy defaults
            temperature = 0.7
            max_tokens = 2048
            skill_id = None
        
        # Construct prompt from blueprint
        full_prompt = f"{blueprint_prompt['system']}\n\n{blueprint_prompt['user']}"
        MAX_PROMPT_CHARS = 8000  # ~2000 tokens
        
        if len(full_prompt) > MAX_PROMPT_CHARS:
            logger.warning(f"Prompt too large ({len(full_prompt)} chars), truncating to {MAX_PROMPT_CHARS}")
            full_prompt = full_prompt[:MAX_PROMPT_CHARS] + "\n\n[Content truncated due to size]"
        
        # Obtain LLM client from provider
        try:
            client = get_llm_client()
        except RuntimeError as e:
            logger.error(f"LLMRunner: No LLM available for batch {batch_config['batch_id']}: {e}")
            return None
        
        try:
            # Log skill ID if available
            skill_log = f" (Skill: {skill_id})" if skill_id else ""
            logger.info(f"LLMRunner: Calling LLM for Batch {batch_config['batch_id']} ({fmt}){skill_log}...")
            logger.debug(f"Prompt size: {len(full_prompt)} chars, Temperature: {temperature}")
            
            response = client.generate_content(
                full_prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            if response is None:
                logger.error(f"LLMRunner: generate_content returned None for batch {batch_config['batch_id']}")
                return None
            
            raw_text = response.text
            
            # Strict JSON return
            try:
                parsed_data = json.loads(raw_text)
                logger.info(f"LLMRunner: Successfully parsed JSON for batch {batch_config['batch_id']}")
                return parsed_data
            except json.JSONDecodeError:
                logger.error(f"LLMRunner: Failed to parse JSON for batch {batch_config['batch_id']}")
                logger.debug(f"Raw Output: {raw_text[:500]}")
                return None
                
        except Exception as e:
            logger.error(f"LLMRunner: Critical Error for batch {batch_config['batch_id']}: {e}")
            return None

    @staticmethod
    def execute(packet: "SkillPacket", context: str = "") -> Optional[Dict[str, Any]]:
        """
        Execute a compiled SkillPacket against the active LLM provider.
        
        Args:
            packet: Compiled SkillPacket from SkillCompiler
            context: Optional context to append (if not already in prompt)
            
        Returns:
            Parsed JSON result or None
        """
        # Deferred import to avoid circular dependencies
        from backend.utils.skill_compiler import SkillPacket
        
        if not isinstance(packet, SkillPacket):
            logger.error(f"LLMRunner: Invalid packet type: {type(packet)}")
            return None
            
        # Extract params
        llm_params = packet.llm_params
        temperature = llm_params.get('temperature', 0.7)
        max_tokens = llm_params.get('max_tokens', 2048)
        
        # Obtain LLM client from provider
        try:
            client = get_llm_client()
        except RuntimeError as e:
            logger.error(f"LLMRunner: No LLM available for skill {packet.skill_id}: {e}")
            return None
        
        try:
            logger.info(f"LLMRunner: Executing Skill {packet.skill_id} ({packet.format_type})...")
            
            response = client.generate_content(
                packet.system_prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            if response is None:
                logger.error(f"LLMRunner: generate_content returned None for skill {packet.skill_id}")
                return None
            
            raw_text = response.text
            
            # JSON parse with regex fallback
            try:
                parsed = json.loads(raw_text)
                return parsed
            except json.JSONDecodeError:
                # Try to extract JSON from text if raw parse fails
                json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                if json_match:
                    try:
                        return json.loads(json_match.group(0))
                    except json.JSONDecodeError:
                        pass
                logger.error(f"LLMRunner: Failed to parse JSON for skill {packet.skill_id}")
                return None
                
        except Exception as e:
            logger.error(f"LLMRunner: Execution error for skill {packet.skill_id}: {e}")
            return None

