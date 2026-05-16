"""
Auth service configuration — loaded from environment variables.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Service
    SERVICE_NAME: str = "auth-svc"
    DEBUG: bool = False

    # Database (Postgres via pgBouncer)
    DATABASE_URL: str = "postgresql://proctoai:proctoai@localhost:6432/proctoai"

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Security
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_MINUTES: int = 30
    BCRYPT_ROUNDS: int = 12

    # Redis (for token blacklist / rate limiting)
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
