from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    SERVICE_NAME: str = "interview-svc"
    DEBUG: bool = False
    DATABASE_URL: str = "postgresql://proctoai:proctoai@localhost:6432/proctoai"
    REDIS_URL: str = "redis://localhost:6379/0"
    JWT_SECRET_KEY: str = "change-me-in-production"
    CORS_ORIGINS: str = "http://localhost:3000"

    # LiveKit
    LIVEKIT_URL: str = "http://localhost:7880"
    LIVEKIT_API_KEY: str = ""
    LIVEKIT_API_SECRET: str = ""

    # Proctoring service
    PROCTORING_SVC_URL: str = "http://localhost:8001"

    # S3 / MinIO
    S3_ENDPOINT: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET: str = "interview-presentations"

    # Upload limits
    MAX_UPLOAD_SIZE_MB: int = 50

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
