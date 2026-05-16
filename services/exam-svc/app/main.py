"""
Exam Service — FastAPI application entry point.

Run:
    uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from app.core.config import get_settings
from app.core.database import get_engine, Base
from app.api.routes import router as exam_router

logger = logging.getLogger("exam-svc")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info(f"Starting {settings.SERVICE_NAME}")
    if settings.DEBUG:
        Base.metadata.create_all(bind=get_engine())
    yield
    logger.info(f"Shutting down {settings.SERVICE_NAME}")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="ProctoAI Exam Service",
        version="1.0.0",
        docs_url="/docs",
        lifespan=lifespan,
    )

    origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(exam_router)

    @app.get("/health", tags=["infra"])
    def health():
        return {"status": "ok", "service": settings.SERVICE_NAME}

    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    return app


app = create_app()
