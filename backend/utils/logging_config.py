
import logging
import logging.config
import os
from pathlib import Path

def setup_logging(name: str = "backend", log_file: str = "app.log", level: int = logging.INFO):
    """
    Setup standardized logging configuration.
    
    Args:
        name: Logger name (usually __name__)
        log_file: Filename for the log file
        level: Logging level (default INFO)
    """
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Define log format
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear existing handlers to avoid duplicates
    if root_logger.handlers:
        root_logger.handlers.clear()
    
    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)
    root_logger.addHandler(console_handler)
    
    # File Handler
    file_handler = logging.FileHandler(log_dir / log_file)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    root_logger.addHandler(file_handler)
    
    # Silence noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.INFO)
    logging.getLogger("socketio").setLevel(logging.WARNING)
    logging.getLogger("engineio").setLevel(logging.WARNING)
    
    logger = logging.getLogger(name)
    logger.info(f"Logging configured for {name}. Level: {logging.getLevelName(level)}")
    
    return logger
