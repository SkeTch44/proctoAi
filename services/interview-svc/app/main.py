"""
Interview Service — FastAPI application entry point.

Run:
    uvicorn app.main:app --host 0.0.0.0 --port 8005 --reload
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from app.core.config import get_settings
from app.core.error_handlers import register_exception_handlers
from app.api.v1.sessions import router as sessions_router
from app.api.v1.participants import router as participants_router
from app.api.v1.presentations import router as presentations_router
from app.api.v1.webhooks import router as webhooks_router
from app.api.v1.cheat_events import router as cheat_events_router
from app.services.timeout_manager import get_timeout_manager

logger = logging.getLogger("interview-svc")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info(f"Starting {settings.SERVICE_NAME}")

    # Start the timeout manager background worker
    timeout_manager = get_timeout_manager()
    await timeout_manager.start_worker()

    yield

    # Stop the timeout manager and clean up
    await timeout_manager.close()
    logger.info(f"Shutting down {settings.SERVICE_NAME}")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="ProctoAI Interview Service",
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

    register_exception_handlers(app)

    app.include_router(sessions_router)
    app.include_router(participants_router)
    app.include_router(presentations_router)
    app.include_router(webhooks_router)
    app.include_router(cheat_events_router)

    @app.get("/health", tags=["infra"])
    def health():
        return {"status": "ok", "service": settings.SERVICE_NAME}

    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    return app


app = create_app()
