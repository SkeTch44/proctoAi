# backend/config.py

import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env at project root
load_dotenv()

class Config:
    """Base configuration for the proctored exam platform."""

    # Flask settings
    _default_secret = "change-me-in-production"
    SECRET_KEY = os.getenv("SECRET_KEY", _default_secret)
    DEBUG = os.getenv("FLASK_ENV", "development") == "development"
    
    if not DEBUG and SECRET_KEY == _default_secret:
        raise ValueError("CRITICAL: SECRET_KEY not set in production environment!")

    # JWT settings
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-secret-key")
    JWT_ALGORITHM = "HS256"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.getenv("JWT_EXPIRES_HOURS", "24")))

    # Database settings
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///exam_platform.db")

    # Upload settings
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_FILE_SIZE", 50 * 1024 * 1024))  # 50MB
    ALLOWED_EXTENSIONS = set(os.getenv("ALLOWED_EXTENSIONS", "pdf,docx").split(","))

    # CORS settings
    # CORS settings
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

    # Proctoring thresholds
    SUSPICION_THRESHOLD = float(os.getenv("SUSPICION_THRESHOLD", "50"))
    FACE_CONFIDENCE_THRESHOLD = float(os.getenv("FACE_CONFIDENCE_THRESHOLD", "0.8"))
    EMOTION_ALERT_THRESHOLD = float(os.getenv("EMOTION_ALERT_THRESHOLD", "0.7"))
    GAZE_THRESHOLD = float(os.getenv("GAZE_THRESHOLD", "0.15"))

    # Rate limiting
    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", "200 per day;50 per hour")

    # AI keys
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    GOOGLE_TRANSLATE_API_KEY = os.getenv("GOOGLE_TRANSLATE_API_KEY", "")

    # RAG engine
    RAG_VECTOR_PATH = os.getenv("RAG_VECTOR_PATH", "backend/db/rag_store/")

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "logs/app.log")

    # Celery
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

    # Local LLM (Ollama)
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

class TestingConfig(Config):
    TESTING = True
    DATABASE_URL = "sqlite:///:memory:"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)

# Factory mapping
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig
}
