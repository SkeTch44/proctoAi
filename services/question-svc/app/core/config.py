from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    SERVICE_NAME: str = "question-svc"
    DEBUG: bool = False
    DATABASE_URL: str = "postgresql://proctoai:proctoai@localhost:6432/proctoai"
    REDIS_URL: str = "redis://localhost:6379/0"
    JWT_SECRET_KEY: str = "change-me-in-production"
    CORS_ORIGINS: str = "http://localhost:3000"

    # LLM
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1:8b"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # Uploads
    UPLOAD_DIR: str = "/tmp/question-svc-uploads"
    MAX_UPLOAD_MB: int = 50

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
