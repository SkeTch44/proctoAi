import json
import logging
import requests
from typing import Dict, Any, Optional
from backend.config import Config

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
        Executes the prompt against the configured LLM.
        
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
        
        # Construct payload for Ollama
        payload = {
            "model": Config.OLLAMA_MODEL,
            "prompt": "",  # Will be set below after size check
            "stream": False,
            "options": {
                "temperature": temperature,  # Skill-specific or default
                "num_predict": max_tokens,   # Skill-specific or default
                "top_p": 0.9
            },
            "format": "json"  # Force Ollama JSON mode
        }
        
        # [FIX] Limit prompt size to prevent Ollama crashes
        full_prompt = f"{blueprint_prompt['system']}\n\n{blueprint_prompt['user']}"
        MAX_PROMPT_CHARS = 8000  # ~2000 tokens for llama3.1
        
        if len(full_prompt) > MAX_PROMPT_CHARS:
            logger.warning(f"Prompt too large ({len(full_prompt)} chars), truncating to {MAX_PROMPT_CHARS}")
            full_prompt = full_prompt[:MAX_PROMPT_CHARS] + "\n\n[Content truncated due to size]"
        
        payload["prompt"] = full_prompt
        
        try:
            # [UPSKILL] Log skill ID if available
            skill_log = f" (Skill: {skill_id})" if skill_id else ""
            logger.info(f"LLMRunner: Calling Ollama for Batch {batch_config['batch_id']} ({fmt}){skill_log}...")
            logger.debug(f"Prompt size: {len(full_prompt)} chars, Temperature: {temperature}")
            
            response = requests.post(
                f"{Config.OLLAMA_BASE_URL}/api/generate",
                json=payload,
                timeout=120  # Strict timeout enforced by Runner
            )
            
            # [FIX] Log detailed error before raising
            if response.status_code != 200:
                logger.error(f"Ollama returned {response.status_code}: {response.text[:500]}")
            
            response.raise_for_status()
            
            result = response.json()
            raw_text = result.get('response', '')
            
            # Phase 4 Rule: Strict JSON return
            try:
                parsed_data = json.loads(raw_text)
                logger.info(f"LLMRunner: Successfully parsed JSON for batch {batch_config['batch_id']}")
                return parsed_data
            except json.JSONDecodeError:
                logger.error(f"LLMRunner: Failed to parse JSON for batch {batch_config['batch_id']}")
                logger.debug(f"Raw Output: {raw_text[:500]}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error(f"LLMRunner: Timeout for batch {batch_config['batch_id']}")
            return None
        except Exception as e:
            logger.error(f"LLMRunner: Critical Error for batch {batch_config['batch_id']}: {e}")
            return None

    @staticmethod
    def execute(packet: "SkillPacket", context: str = "") -> Optional[Dict[str, Any]]:
        """
        Execute a compiled SkillPacket against Ollama.
        
        Args:
            packet: Compiled SkillPacket from SkillCompiler
            context: Optional context to append (if not already in prompt)
            
        Returns:
            Parsed JSON result or None
        """
        # Deferred import to avoid circular dependencies
        from backend.utils.skill_compiler import SkillPacket
        import requests
        import json
        import re
        from typing import Dict, Any, Optional

        if not isinstance(packet, SkillPacket):
            logger.error(f"LLMRunner: Invalid packet type: {type(packet)}")
            return None
            
        # Extract params
        llm_params = packet.llm_params
        temperature = llm_params.get('temperature', 0.7)
        max_tokens = llm_params.get('max_tokens', 2048)
        
        # Construct payload
        payload = {
            "model": Config.OLLAMA_MODEL,
            "prompt": packet.system_prompt,  # Already substituted
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "top_p": 0.9
            },
            "format": "json"
        }
        
        try:
            logger.info(f"LLMRunner: Executing Skill {packet.skill_id} ({packet.format_type})...")
            
            response = requests.post(
                f"{Config.OLLAMA_BASE_URL}/api/generate",
                json=payload,
                timeout=120
            )
            
            if response.status_code != 200:
                logger.error(f"Ollama returned {response.status_code}: {response.text[:500]}")
                return None
                
            response.raise_for_status()
            result = response.json()
            raw_text = result.get('response', '')
            
            # Use validation schema if we had a Validator, but for now just JSON parse
            try:
                parsed = json.loads(raw_text)
                return parsed
            except json.JSONDecodeError:
                # Try to extract JSON from text if raw parse fails
                json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                if json_match:
                    try:
                        return json.loads(json_match.group(0))
                    except:
                        pass
                logger.error(f"LLMRunner: Failed to parse JSON for skill {packet.skill_id}")
                return None
                
        except Exception as e:
            logger.error(f"LLMRunner: Execution error for skill {packet.skill_id}: {e}")
            return None

