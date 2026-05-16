import threading
import logging
from typing import Dict, Any, Callable, Optional

# Configure logging for production
logger = logging.getLogger(__name__)

class LazyLoader:
    """
    Thread-safe Singleton Lazy Loader for heavy backend components.
    Ensures models and services are loaded exactly once and provides
    fault-tolerance through reset capabilities.
    """
    _instances: Dict[str, Any] = {}
    _locks: Dict[str, threading.Lock] = {}
    _global_lock = threading.Lock()

    @classmethod
    def get(cls, key: str, loader_func: Callable[[], Any]) -> Any:
        """
        Get or create a lazy-loaded instance for the given key.
        
        Args:
            key: Unique identifier for the component (e.g., 'llm', 'yolo')
            loader_func: Function to call if the component isn't loaded yet
            
        Returns:
            The loaded component instance
        """
        # Ensure a lock exists for this key in a thread-safe way
        if key not in cls._locks:
            with cls._global_lock:
                if key not in cls._locks:
                    cls._locks[key] = threading.Lock()

        # Double-checked locking pattern
        if key not in cls._instances:
            with cls._locks[key]:
                if key not in cls._instances:
                    logger.info(f"[LazyLoader] Loading component: {key}...")
                    try:
                        instance = loader_func()
                        cls._instances[key] = instance
                        logger.info(f"[LazyLoader] Component {key} loaded successfully.")
                    except Exception as e:
                        logger.error(f"[LazyLoader] Failed to load component {key}: {str(e)}")
                        raise e
        
        return cls._instances[key]

    @classmethod
    def reset(cls, key: str):
        """
        Remove a cached instance, forcing a reload on next access.
        Used for handling model crashes or hot reloads.
        """
        with cls._global_lock:
            if key in cls._instances:
                logger.warning(f"[LazyLoader] Resetting component: {key}")
                del cls._instances[key]
            else:
                logger.debug(f"[LazyLoader] No instance found to reset for key: {key}")

    @classmethod
    def is_loaded(cls, key: str) -> bool:
        """Check if a component is currently loaded in memory."""
        return key in cls._instances

    @classmethod
    def clear_all(cls):
        """Clear all loaded instances."""
        with cls._global_lock:
            logger.warning("[LazyLoader] Clearing all components from memory.")
            cls._instances.clear()
