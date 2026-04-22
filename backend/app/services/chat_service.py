from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.db.models import Conversation, Message
from backend.app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationSummary,
    DeleteConversationResponse,
    SourceResponse,
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
            role="assistant",
            content_markdown=assistant.answer,
            route=assistant.route,
            citations_json=[],
            sources_json=[item.model_dump() for item in assistant.sources],
        )
        self.db.add(assistant_record)
        conversation.updated_at = datetime.now(timezone.utc)
        self.db.flush()
        self.db.commit()

        return ChatResponse(
            answer=assistant.answer,
            sources=assistant.sources,
            conversation_id=conversation.id,
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
            first_user_message = next(
                (message.content_markdown for message in conversation.messages if message.role == "user"),
                "",
            )
            preview = " ".join(first_user_message.split()).strip()
            if len(preview) > 80:
                preview = preview[:77].rstrip() + "..."
            items.append(
                ConversationSummary(
                    conversation_id=conversation.id,
                    first_message=preview or conversation.title,
                    created_at=conversation.created_at,
                )
            )
        return items

    def get_conversation(self, conversation_id: str) -> list[StoredMessage] | None:
        query = (
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.id == conversation_id)
        )
        conversation = self.db.scalar(query)
        if conversation is None:
            return None

        return [
            StoredMessage(
                role=message.role,
                content=message.content_markdown,
                sources=[SourceResponse(**item) for item in (message.sources_json or [])],
                created_at=message.created_at,
            )
            for message in conversation.messages
        ]

    def delete_conversation(self, conversation_id: str) -> DeleteConversationResponse | None:
        conversation = self.db.get(Conversation, conversation_id)
        if conversation is None:
            return None

        self.db.delete(conversation)
        self.db.commit()
        return DeleteConversationResponse(deleted=True, conversation_id=conversation_id)

    def _get_or_create_conversation(self, payload: ChatRequest) -> Conversation:
        if payload.conversation_id:
            conversation = self.db.get(Conversation, payload.conversation_id)
            if conversation is not None:
                return conversation

        if payload.conversation_id:
            conversation = Conversation(
                id=payload.conversation_id,
                title=self._title_from_message(payload.message),
            )
        else:
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
