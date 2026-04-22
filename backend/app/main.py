from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes import chat, conversations, health
from backend.app.core.config import get_settings
from backend.app.db import models  # noqa: F401
from backend.app.db.session import Base, engine
from backend.app.services.bootstrap import bootstrap_chroma_if_needed
from backend.app.services.pipeline_service import get_pipeline_service


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):  # noqa: ARG001
        Base.metadata.create_all(bind=engine)
        bootstrap_chroma_if_needed(settings.pipeline_config)
        get_pipeline_service().warmup()
        yield

    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description="Public API for the UGP PLD Copilot chatbot.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )

    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(chat.router, prefix="/api", tags=["chat"])
    app.include_router(conversations.router, prefix="/api", tags=["conversations"])
    return app


app = create_app()
