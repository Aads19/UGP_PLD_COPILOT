from __future__ import annotations

from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.db.models import Conversation, Message
from backend.app.db.session import Base
from backend.app.schemas.chat import ChatRequest, CitationResponse, SourceResponse
from backend.app.services.chat_service import ChatService


class FakePipelineService:
    def run(self, message: str) -> SimpleNamespace:
        return SimpleNamespace(
            role="assistant",
            route="database",
            content_markdown=f"Answering: {message}",
            citations=[
                CitationResponse(
                    doi="10.1000/test",
                    title="Example paper",
                    url="https://doi.org/10.1000/test",
                )
            ],
            sources=[
                SourceResponse(
                    chunk_id="chunk-1",
                    title="Example paper",
                    doi="10.1000/test",
                    snippet="Evidence snippet",
                    score=0.1,
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
    assert response.message.citations[0].doi == "10.1000/test"
