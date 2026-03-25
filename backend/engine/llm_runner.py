import json
import logging
import requests
from typing import Dict, Any, Optional
from backend.config import Config

logger = logging.getLogger(__name__)

# Use the new google-genai SDK (replaces deprecated google.generativeai)
try:
    from google import genai
    from google.genai import types
    genai_available = True
except ImportError:
    genai_available = False
    logger.warning("google-genai not installed, Gemini functions disabled")

class LLMRunner:
    """
    Phase 4 & 9: LLM Runner
    Responsibility: Execute Blueprint against Model (Gemini / Ollama)
    - Gemini Cloud as primary (fast, high-quality)
    - Ollama local as fallback (offline, no quota limits)
    - Automatic fallback on any Gemini failure
    """

    @staticmethod
    def _run_gemini(full_prompt: str, temperature: float, batch_id: str) -> Optional[Any]:
        if not genai_available or not Config.GEMINI_API_KEY:
            logger.warning(f"Gemini skipped for batch {batch_id}: SDK or API_KEY missing.")
            return None

        try:
            client = genai.Client(api_key=Config.GEMINI_API_KEY)

            logger.info(f"LLMRunner: Calling Gemini (gemini-2.0-flash) for Batch {batch_id}...")

            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json',
                    temperature=temperature
                )
            )

            try:
                parsed_data = json.loads(response.text)
                logger.info(f"LLMRunner: Successfully parsed JSON from Gemini for batch {batch_id}")
                return parsed_data
            except json.JSONDecodeError:
                logger.error(f"LLMRunner: Gemini returned invalid JSON for batch {batch_id}")
                logger.debug(f"Raw Output: {response.text[:500]}")
                return None

        except Exception as e:
            logger.error(f"LLMRunner: Gemini API Error for batch {batch_id}: {e}")
            return None

    @staticmethod
    def _run_ollama(full_prompt: str, temperature: float, max_tokens: int, batch_id: str, fmt: str) -> Optional[Any]:
        payload = {
            "model": Config.OLLAMA_MODEL,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "top_p": 0.9
            },
            "format": "json"
        }

        try:
            logger.info(f"LLMRunner: Calling Ollama for Batch {batch_id} ({fmt})...")

            response = requests.post(
                f"{Config.OLLAMA_BASE_URL}/api/generate",
                json=payload,
                timeout=300
            )

            if response.status_code != 200:
                logger.error(f"Ollama returned {response.status_code}: {response.text[:500]}")

            response.raise_for_status()

            result = response.json()
            raw_text = result.get('response', '')

            try:
                parsed_data = json.loads(raw_text)
                logger.info(f"LLMRunner: Successfully parsed JSON from Ollama for batch {batch_id}")
                return parsed_data
            except json.JSONDecodeError:
                logger.error(f"LLMRunner: Failed to parse JSON from Ollama for batch {batch_id}")
                logger.debug(f"Raw Output: {raw_text[:500]}")
                return None

        except requests.exceptions.Timeout:
            logger.error(f"LLMRunner: Timeout for Ollama batch {batch_id}")
            return None
        except Exception as e:
            logger.error(f"LLMRunner: Critical Ollama Error for batch {batch_id}: {e}")
            return None

    @staticmethod
    def run_batch(blueprint_prompt: Dict, batch_config: Dict, skill_metadata: Optional[Dict] = None) -> Optional[Any]:
        """
        Executes the prompt against the configured LLMs (Gemini -> Fallback to Ollama).
        """
        fmt = batch_config['type']
        batch_id = batch_config.get('batch_id', 'UNKNOWN')

        if skill_metadata and 'llm_params' in skill_metadata:
            llm_params = skill_metadata['llm_params']
            temperature = llm_params.get('temperature', 0.7)
            max_tokens = llm_params.get('max_tokens', 2048)
        else:
            temperature = 0.7
            max_tokens = 2048

        full_prompt = f"{blueprint_prompt['system']}\n\n{blueprint_prompt['user']}"
        MAX_PROMPT_CHARS = 8000

        if len(full_prompt) > MAX_PROMPT_CHARS:
            logger.warning(f"Prompt too large ({len(full_prompt)} chars), truncating to {MAX_PROMPT_CHARS}")
            full_prompt = full_prompt[:MAX_PROMPT_CHARS] + "\n\n[Content truncated due to size]"

        # Phase 9: Try Gemini first
        gemini_result = LLMRunner._run_gemini(full_prompt, temperature, str(batch_id))
        if gemini_result is not None:
            return gemini_result

        # Phase 9: Fallback to local Ollama
        logger.warning(f"Falling back to local Ollama model ({Config.OLLAMA_MODEL}) for batch {batch_id}")
        return LLMRunner._run_ollama(full_prompt, temperature, max_tokens, str(batch_id), fmt)

    @staticmethod
    def execute(packet: "SkillPacket", context: str = "") -> Optional[Dict[str, Any]]:
        """
        Execute a compiled SkillPacket against Gemini (fallback Ollama).
        """
        from backend.utils.skill_compiler import SkillPacket

        if not isinstance(packet, SkillPacket):
            return None

        llm_params = packet.llm_params
        temperature = llm_params.get('temperature', 0.7)
        max_tokens = llm_params.get('max_tokens', 2048)

        # Try Gemini
        gemini_result = LLMRunner._run_gemini(packet.system_prompt, temperature, f"Skill-{packet.skill_id}")
        if gemini_result is not None:
            return gemini_result

        # Fallback Ollama
        logger.warning(f"Skill {packet.skill_id}: Falling back to local Ollama model")
        return LLMRunner._run_ollama(packet.system_prompt, temperature, max_tokens, f"Skill-{packet.skill_id}", packet.format_type)
