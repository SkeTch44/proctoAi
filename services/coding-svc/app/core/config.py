from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    SERVICE_NAME: str = "coding-svc"
    DEBUG: bool = False
    DATABASE_URL: str = "postgresql://proctoai:proctoai@localhost:6432/proctoai"
    REDIS_URL: str = "redis://localhost:6379/0"
    JWT_SECRET_KEY: str = "change-me-in-production"
    CORS_ORIGINS: str = "http://localhost:3000"

    # Judge0 sandbox
    JUDGE0_URL: str = "http://localhost:2358"
    JUDGE0_API_KEY: str = ""

    # AI Scorer (Ollama)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1:8b"

    # Limits
    MAX_EXECUTION_TIME_SEC: int = 10
    MAX_MEMORY_KB: int = 256000  # 256 MB

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
