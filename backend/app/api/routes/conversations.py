from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_db, get_pipeline
from backend.app.schemas.chat import ConversationSummary, DeleteConversationResponse, StoredMessage
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


@router.get("/conversations/{conversation_id}", response_model=list[StoredMessage])
def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    pipeline: PipelineService = Depends(get_pipeline),
) -> list[StoredMessage]:
    service = ChatService(db=db, pipeline=pipeline)
    conversation = service.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )
    return conversation


@router.delete("/conversations/{conversation_id}", response_model=DeleteConversationResponse)
def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    pipeline: PipelineService = Depends(get_pipeline),
) -> DeleteConversationResponse:
    service = ChatService(db=db, pipeline=pipeline)
    result = service.delete_conversation(conversation_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )
    return result
