from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_db, get_limiter, get_pipeline
from backend.app.schemas.chat import ChatRequest, ChatResponse
from backend.app.services.chat_service import ChatService
from backend.app.services.pipeline_service import PipelineExecutionError, PipelineService
from backend.app.services.rate_limiter import RateLimiter

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def create_chat_reply(
    payload: ChatRequest,
    request: Request,
    db: Session = Depends(get_db),
    pipeline: PipelineService = Depends(get_pipeline),
    limiter: RateLimiter = Depends(get_limiter),
) -> ChatResponse:
    client_key = request.client.host if request.client else "anonymous"
    if not limiter.allow(client_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please wait a moment and try again.",
        )

    service = ChatService(db=db, pipeline=pipeline)
    try:
        return service.create_reply(payload)
    except PipelineExecutionError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
