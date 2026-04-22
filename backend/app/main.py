from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes import chat, conversations, health
from backend.app.core.config import get_settings
from backend.app.db import models  # noqa: F401
from backend.app.db.session import Base, engine
from backend.app.services.bootstrap import bootstrap_chroma_if_needed


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description="Public API for the UGP PLD Copilot chatbot.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(chat.router, prefix="/api", tags=["chat"])
    app.include_router(conversations.router, prefix="/api", tags=["conversations"])

    @app.on_event("startup")
    def on_startup() -> None:
        Base.metadata.create_all(bind=engine)
        bootstrap_chroma_if_needed(settings.pipeline_config)

    return app


app = create_app()
