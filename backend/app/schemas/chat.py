from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SourceResponse(BaseModel):
    doi: str = ""
    title: str = ""
    chunk_idx: int = 0


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceResponse] = Field(default_factory=list)
    conversation_id: str


class ConversationSummary(BaseModel):
    conversation_id: str
    first_message: str
    created_at: datetime | None = None


class StoredMessage(BaseModel):
    role: str
    content: str
    sources: list[SourceResponse] = Field(default_factory=list)
    created_at: datetime


class HealthResponse(BaseModel):
    status: str = "ok"


class DeleteConversationResponse(BaseModel):
    deleted: bool
    conversation_id: str
