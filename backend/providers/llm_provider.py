import logging
from backend.utils.lazy_loader import LazyLoader
from backend.utils.llm_client import LLMFactory

logger = logging.getLogger(__name__)

def _load_llm():
    """Inner loader function for LLM client."""
    client = LLMFactory.create_client()
    if not client:
        raise RuntimeError("No LLM client could be initialized via LLMFactory.")
    return client

def get_llm_client():
    """
    Get or reload the LLM client instance.
    Includes fault-tolerance: if the client is not alive, resets and reloads.
    On health check failure, resets the cached instance and re-creates via
    LLMFactory.create_client(), which re-attempts MiniMax first (enabling
    recovery to primary) before falling back to Ollama.
    """
    client = LazyLoader.get("llm", _load_llm)
    
    # Fault-tolerance: Health check and auto-reset
    try:
        if hasattr(client, 'health_check') and not client.health_check():
            provider_name = type(client).__name__
            logger.warning(
                f"[LLMProvider] {provider_name} health check failed. "
                f"Resetting and attempting fallback via LLMFactory."
            )
            LazyLoader.reset("llm")
            client = LazyLoader.get("llm", _load_llm)
            new_provider_name = type(client).__name__
            logger.info(
                f"[LLMProvider] Fallback transition complete: "
                f"{provider_name} → {new_provider_name}"
            )
    except RuntimeError:
        # Re-raise RuntimeError from _load_llm (no provider available)
        raise
    except Exception as e:
        provider_name = type(client).__name__
        logger.warning(
            f"[LLMProvider] {provider_name} health check raised exception: {e}. "
            f"Resetting and attempting fallback via LLMFactory."
        )
        LazyLoader.reset("llm")
        client = LazyLoader.get("llm", _load_llm)
        new_provider_name = type(client).__name__
        logger.info(
            f"[LLMProvider] Fallback transition complete: "
            f"{provider_name} → {new_provider_name}"
        )
        
    return client
