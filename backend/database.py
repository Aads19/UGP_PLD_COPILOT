from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.db.models import Conversation, Message
from backend.app.db.session import Base, SessionLocal, engine


def create_schema() -> None:
    Base.metadata.create_all(bind=engine)


@contextmanager
def session_scope() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def save_conversation(conversation_id: str, title: str) -> None:
    with session_scope() as session:
        conversation = session.get(Conversation, conversation_id)
        if conversation is None:
            session.add(Conversation(id=conversation_id, title=title))


def save_message(
    conversation_id: str,
    role: str,
    content: str,
    *,
    sources: list[dict] | None = None,
    route: str | None = None,
) -> None:
    with session_scope() as session:
        session.add(
            Message(
                conversation_id=conversation_id,
                role=role,
                content_markdown=content,
                sources_json=sources or [],
                route=route,
                citations_json=[],
            )
        )


def list_conversations() -> list[Conversation]:
    with session_scope() as session:
        query = (
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .order_by(Conversation.updated_at.desc(), Conversation.created_at.desc())
        )
        return list(session.scalars(query).all())


def get_conversation(conversation_id: str) -> Conversation | None:
    with session_scope() as session:
        query = (
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.id == conversation_id)
        )
        return session.scalar(query)


def delete_conversation(conversation_id: str) -> bool:
    with session_scope() as session:
        conversation = session.get(Conversation, conversation_id)
        if conversation is None:
            return False
        session.delete(conversation)
        return True
