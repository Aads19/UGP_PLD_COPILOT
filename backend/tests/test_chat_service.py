from __future__ import annotations

from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.db.models import Conversation, Message
from backend.app.db.session import Base
from backend.app.schemas.chat import ChatRequest, SourceResponse
from backend.app.services.chat_service import ChatService


class FakePipelineService:
    def run(self, message: str) -> SimpleNamespace:
        return SimpleNamespace(
            answer=f"Answering: {message}",
            route="database",
            sources=[
                SourceResponse(
                    doi="10.1000/test",
                    title="Example paper",
                    chunk_idx=7,
                )
            ],
        )


def build_session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, future=True)()


def test_create_reply_persists_messages() -> None:
    db = build_session()
    service = ChatService(db=db, pipeline=FakePipelineService())

    response = service.create_reply(ChatRequest(message="What does the corpus say about PLD texture?"))

    conversation = db.get(Conversation, response.conversation_id)
    assert conversation is not None

    messages = db.query(Message).filter(Message.conversation_id == response.conversation_id).all()
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"
    assert response.sources[0].doi == "10.1000/test"
    assert response.answer.startswith("Answering:")


def test_delete_conversation_removes_messages() -> None:
    db = build_session()
    service = ChatService(db=db, pipeline=FakePipelineService())
    response = service.create_reply(ChatRequest(message="Explain PLD growth conditions."))

    deletion = service.delete_conversation(response.conversation_id)

    assert deletion is not None
    assert deletion.deleted is True
    assert db.get(Conversation, response.conversation_id) is None
