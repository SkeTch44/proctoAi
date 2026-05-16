"""
Auth Service — FastAPI application entry point.

Run:
    uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from app.core.config import get_settings
from app.core.database import get_engine, Base
from app.api.routes import router as auth_router

logger = logging.getLogger("auth-svc")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hooks."""
    settings = get_settings()
    logger.info(f"Starting {settings.SERVICE_NAME}")

    # Ensure tables exist (dev convenience; prod uses Alembic)
    if settings.DEBUG:
        Base.metadata.create_all(bind=get_engine())
        logger.info("DEV mode: tables created via create_all")

    yield

    logger.info(f"Shutting down {settings.SERVICE_NAME}")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="ProctoAI Auth Service",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS
    origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes
    app.include_router(auth_router)

    # Health check
    @app.get("/health", tags=["infra"])
    def health():
        return {"status": "ok", "service": settings.SERVICE_NAME}

    # Prometheus metrics
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    return app


app = create_app()
