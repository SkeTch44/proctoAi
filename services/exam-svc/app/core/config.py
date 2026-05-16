from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    SERVICE_NAME: str = "exam-svc"
    DEBUG: bool = False
    DATABASE_URL: str = "postgresql://proctoai:proctoai@localhost:6432/proctoai"
    REDIS_URL: str = "redis://localhost:6379/0"
    AUTH_SERVICE_URL: str = "http://localhost:8001"
    CORS_ORIGINS: str = "http://localhost:3000"
    JWT_SECRET_KEY: str = "change-me-in-production"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
