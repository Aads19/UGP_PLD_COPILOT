from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CitationResponse(BaseModel):
    doi: str = ""
    title: str = ""
    url: str | None = None


class SourceResponse(BaseModel):
    chunk_id: str
    title: str = ""
    doi: str = ""
    snippet: str
    score: float | None = None


class AssistantMessageResponse(BaseModel):
    id: str
    role: str
    content_markdown: str
    route: str
    citations: list[CitationResponse] = Field(default_factory=list)
    sources: list[SourceResponse] = Field(default_factory=list)
    created_at: datetime


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    conversation_id: str
    message: AssistantMessageResponse


class ConversationSummary(BaseModel):
    id: str
    title: str
    preview: str
    updated_at: datetime | None = None
    created_at: datetime | None = None


class StoredMessage(BaseModel):
    id: str
    role: str
    content_markdown: str
    route: str | None = None
    citations: list[CitationResponse] = Field(default_factory=list)
    sources: list[SourceResponse] = Field(default_factory=list)
    created_at: datetime


class ConversationDetail(BaseModel):
    id: str
    title: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    messages: list[StoredMessage] = Field(default_factory=list)


class HealthResponse(BaseModel):
    ok: bool
    app_env: str
    database_connected: bool
    chroma: dict
    groq_configured: bool
