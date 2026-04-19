from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.db.models import Conversation, Message
from backend.app.schemas.chat import (
    AssistantMessageResponse,
    ChatRequest,
    ChatResponse,
    ConversationDetail,
    ConversationSummary,
    StoredMessage,
)
from backend.app.services.pipeline_service import PipelineService


class ChatService:
    def __init__(self, db: Session, pipeline: PipelineService) -> None:
        self.db = db
        self.pipeline = pipeline

    def create_reply(self, payload: ChatRequest) -> ChatResponse:
        conversation = self._get_or_create_conversation(payload)
        self._persist_user_message(conversation.id, payload.message)

        assistant = self.pipeline.run(payload.message)
        assistant_record = Message(
            conversation_id=conversation.id,
            role=assistant.role,
            content_markdown=assistant.content_markdown,
            route=assistant.route,
            citations_json=[item.model_dump() for item in assistant.citations],
            sources_json=[item.model_dump() for item in assistant.sources],
        )
        self.db.add(assistant_record)
        conversation.updated_at = datetime.now(timezone.utc)
        self.db.flush()
        self.db.refresh(assistant_record)
        self.db.commit()

        return ChatResponse(
            conversation_id=conversation.id,
            message=AssistantMessageResponse(
                id=assistant_record.id,
                role=assistant_record.role,
                content_markdown=assistant_record.content_markdown,
                route=assistant_record.route or "database",
                citations=assistant.citations,
                sources=assistant.sources,
                created_at=assistant_record.created_at,
            ),
        )

    def list_conversations(self) -> list[ConversationSummary]:
        query = (
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .order_by(Conversation.updated_at.desc(), Conversation.created_at.desc())
        )
        conversations = self.db.scalars(query).all()
        items: list[ConversationSummary] = []
        for conversation in conversations:
            preview = ""
            if conversation.messages:
                preview = conversation.messages[-1].content_markdown[:140]
            items.append(
                ConversationSummary(
                    id=conversation.id,
                    title=conversation.title,
                    preview=preview,
                    updated_at=conversation.updated_at,
                    created_at=conversation.created_at,
                )
            )
        return items

    def get_conversation(self, conversation_id: str) -> ConversationDetail | None:
        query = (
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.id == conversation_id)
        )
        conversation = self.db.scalar(query)
        if conversation is None:
            return None

        return ConversationDetail(
            id=conversation.id,
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            messages=[
                StoredMessage(
                    id=message.id,
                    role=message.role,
                    content_markdown=message.content_markdown,
                    route=message.route,
                    citations=message.citations_json or [],
                    sources=message.sources_json or [],
                    created_at=message.created_at,
                )
                for message in conversation.messages
            ],
        )

    def _get_or_create_conversation(self, payload: ChatRequest) -> Conversation:
        if payload.conversation_id:
            conversation = self.db.get(Conversation, payload.conversation_id)
            if conversation is not None:
                return conversation

        conversation = Conversation(title=self._title_from_message(payload.message))
        self.db.add(conversation)
        self.db.flush()
        self.db.refresh(conversation)
        return conversation

    def _persist_user_message(self, conversation_id: str, text: str) -> None:
        record = Message(
            conversation_id=conversation_id,
            role="user",
            content_markdown=text.strip(),
            route="user",
            citations_json=[],
            sources_json=[],
        )
        self.db.add(record)
        self.db.flush()

    @staticmethod
    def _title_from_message(text: str) -> str:
        stripped = " ".join(text.strip().split())
        if len(stripped) <= 80:
            return stripped
        return stripped[:77].rstrip() + "..."
