from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from backend.app.core.config import Settings, get_settings
from backend.app.schemas.chat import HealthResponse, SourceResponse
from pld_copilot.pipeline import PLDCopilotPipeline


class PipelineExecutionError(RuntimeError):
    """Raised when the PLD pipeline cannot produce a safe response."""


@dataclass
class AssistantPayload:
    answer: str
    route: str
    sources: list[SourceResponse]


class PipelineService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.pipeline = PLDCopilotPipeline.from_config(settings.pipeline_config)

    def warmup(self) -> None:
        self.pipeline.warmup()

    def run(self, message: str) -> AssistantPayload:
        try:
            result = self.pipeline.run(message)
        except Exception as exc:  # noqa: BLE001
            raise PipelineExecutionError(
                "The research server is temporarily unavailable. Please try again in a moment."
            ) from exc

        return AssistantPayload(
            answer=result.answer_markdown,
            route=result.route,
            sources=[
                SourceResponse(
                    doi=chunk.doi,
                    title=chunk.title,
                    chunk_idx=chunk.chunk_idx,
                )
                for chunk in result.sources
            ],
        )

    @staticmethod
    def health() -> HealthResponse:
        return HealthResponse(status="ok")


@lru_cache(maxsize=1)
def get_pipeline_service() -> PipelineService:
    return PipelineService(get_settings())
