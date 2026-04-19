from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from backend.app.core.config import Settings, get_settings
from backend.app.schemas.chat import CitationResponse, HealthResponse, SourceResponse
from pld_copilot.pipeline import PLDCopilotPipeline


class PipelineExecutionError(RuntimeError):
    """Raised when the PLD pipeline cannot produce a safe response."""


@dataclass
class AssistantPayload:
    role: str
    route: str
    content_markdown: str
    citations: list[CitationResponse]
    sources: list[SourceResponse]


class PipelineService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.pipeline = PLDCopilotPipeline.from_config(settings.pipeline_config)

    def run(self, message: str) -> AssistantPayload:
        llm_config = self.settings.pipeline_config.llm
        if not llm_config.api_key:
            return AssistantPayload(
                role="assistant",
                route="system",
                content_markdown=(
                    "The PLD copilot backend is online, but model access is not configured yet.\n\n"
                    "Set `GROQ_API_KEY` in the backend environment to enable full literature routing, "
                    "retrieval grading, and source-grounded answer synthesis."
                ),
                citations=[],
                sources=[],
            )

        try:
            result = self.pipeline.run(message)
        except Exception as exc:  # noqa: BLE001
            raise PipelineExecutionError(
                "The PLD copilot is temporarily unavailable. Please retry after checking the model and database configuration."
            ) from exc

        sources = self._extract_sources(result.debug.get("approved_chunks", []))
        citations = self._build_citations(result.citations, sources)
        return AssistantPayload(
            role="assistant",
            route=result.route,
            content_markdown=result.answer_markdown,
            citations=citations,
            sources=sources,
        )

    def health(self) -> HealthResponse:
        llm_config = self.settings.pipeline_config.llm
        chroma_status = self.pipeline.retriever.status()
        return HealthResponse(
            ok=True,
            app_env=self.settings.app_env,
            database_connected=True,
            chroma=chroma_status,
            groq_configured=bool(llm_config.api_key),
        )

    @staticmethod
    def _build_citations(dois: list[str], sources: list[SourceResponse]) -> list[CitationResponse]:
        source_by_doi = {source.doi: source for source in sources if source.doi}
        items: list[CitationResponse] = []
        for doi in dois:
            source = source_by_doi.get(doi)
            items.append(
                CitationResponse(
                    doi=doi,
                    title=source.title if source else "",
                    url=f"https://doi.org/{doi}" if doi else None,
                )
            )
        return items

    @staticmethod
    def _extract_sources(raw_chunks: list[dict]) -> list[SourceResponse]:
        sources: list[SourceResponse] = []
        for raw in raw_chunks:
            snippet = str(raw.get("text", "")).strip()
            if len(snippet) > 320:
                snippet = snippet[:317].rstrip() + "..."
            sources.append(
                SourceResponse(
                    chunk_id=str(raw.get("chunk_id", "")),
                    title=str(raw.get("title", "")),
                    doi=str(raw.get("doi", "")),
                    snippet=snippet,
                    score=raw.get("score"),
                )
            )
        return sources


@lru_cache(maxsize=1)
def get_pipeline_service() -> PipelineService:
    return PipelineService(get_settings())
