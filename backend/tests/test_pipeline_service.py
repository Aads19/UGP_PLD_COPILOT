from __future__ import annotations

from backend.app.schemas.chat import HealthResponse
from backend.app.services.pipeline_service import AssistantPayload, PipelineService


def test_health_returns_ok() -> None:
    health = PipelineService.health()

    assert health == HealthResponse(status="ok")


def test_assistant_payload_keeps_expected_fields() -> None:
    payload = AssistantPayload(
        answer="Grounded answer",
        route="database",
        sources=[],
    )

    assert payload.answer == "Grounded answer"
    assert payload.route == "database"
    assert payload.sources == []
