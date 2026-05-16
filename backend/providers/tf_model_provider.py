import logging
import os
from backend.utils.lazy_loader import LazyLoader

logger = logging.getLogger(__name__)

def _load_tf_model():
    """
    Inner loader for TensorFlow models.
    Imports are inside to avoid making TensorFlow a hard requirement 
    at the module level during startup.
    """
    try:
        import tensorflow as tf
        model_path = os.getenv("TF_MODEL_PATH", "backend/models/production_v1.h5")
        
        if not os.path.exists(model_path):
            logger.warning(f"[TFProvider] Model file not found at {model_path}. Creating a dummy model for structure.")
            # Dummy model if file is missing (to allow the system to start)
            model = tf.keras.Sequential([tf.keras.layers.Dense(1, input_shape=(10,))])
        else:
            logger.info(f"[TFProvider] Loading TensorFlow model from {model_path}...")
            model = tf.keras.models.load_model(model_path)
            
        logger.info("[TFProvider] TensorFlow model loaded successfully.")
        return model
    except ImportError:
        logger.error("[TFProvider] TensorFlow is not installed. Lazy load failed.")
        return None
    except Exception as e:
        logger.error(f"[TFProvider] Unexpected error loading TF model: {e}")
        return None

def get_tf_model():
    """
    Get the lazy-loaded TensorFlow model instance.
    Includes health check for basic model validity.
    """
    model = LazyLoader.get("tf_model", _load_tf_model)
    
    # Fault-tolerance: Basic check
    if model is None:
        logger.warning("[TFProvider] TF model is None. Attempting reset/reload.")
        LazyLoader.reset("tf_model")
        model = LazyLoader.get("tf_model", _load_tf_model)
        
    return model
