from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_db, get_pipeline
from backend.app.schemas.chat import HealthResponse
from backend.app.services.pipeline_service import PipelineService

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check(
    db: Session = Depends(get_db),
    pipeline: PipelineService = Depends(get_pipeline),
) -> HealthResponse:
    db.execute(text("SELECT 1"))
    return pipeline.health()
