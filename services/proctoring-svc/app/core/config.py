from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    SERVICE_NAME: str = "proctoring-svc"
    DEBUG: bool = False
    DATABASE_URL: str = "postgresql://proctoai:proctoai@localhost:6432/proctoai"
    REDIS_URL: str = "redis://localhost:6379/0"
    JWT_SECRET_KEY: str = "change-me-in-production"
    CORS_ORIGINS: str = "http://localhost:3000"

    # Inference
    YOLO_MODEL_PATH: str = "yolov8n.pt"
    BATCH_SIZE: int = 8
    FRAME_SKIP_THRESHOLD: float = 0.92  # perceptual hash similarity to skip

    # Risk engine
    SUSPICION_THRESHOLD: float = 50.0
    FACE_CONFIDENCE_THRESHOLD: float = 0.8

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
