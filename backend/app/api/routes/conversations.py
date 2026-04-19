from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_db, get_pipeline
from backend.app.schemas.chat import ConversationDetail, ConversationSummary
from backend.app.services.chat_service import ChatService
from backend.app.services.pipeline_service import PipelineService

router = APIRouter()


@router.get("/conversations", response_model=list[ConversationSummary])
def list_conversations(
    db: Session = Depends(get_db),
    pipeline: PipelineService = Depends(get_pipeline),
) -> list[ConversationSummary]:
    service = ChatService(db=db, pipeline=pipeline)
    return service.list_conversations()


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    pipeline: PipelineService = Depends(get_pipeline),
) -> ConversationDetail:
    service = ChatService(db=db, pipeline=pipeline)
    conversation = service.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )
    return conversation
