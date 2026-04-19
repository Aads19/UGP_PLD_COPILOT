from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session

from backend.app.db.session import SessionLocal
from backend.app.services.pipeline_service import PipelineService, get_pipeline_service
from backend.app.services.rate_limiter import RateLimiter, get_rate_limiter


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_pipeline() -> PipelineService:
    return get_pipeline_service()


def get_limiter() -> RateLimiter:
    return get_rate_limiter()
