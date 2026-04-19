from __future__ import annotations

from backend.app.schemas.chat import CitationResponse
from backend.app.services.pipeline_service import PipelineService


def test_build_citations_uses_doi_links() -> None:
    sources = PipelineService._extract_sources(
        [
            {
                "chunk_id": "chunk-1",
                "title": "Paper title",
                "doi": "10.1000/test",
                "text": "Evidence text for this paper.",
                "score": 0.12,
            }
        ]
    )

    citations = PipelineService._build_citations(["10.1000/test"], sources)

    assert citations == [
        CitationResponse(
            doi="10.1000/test",
            title="Paper title",
            url="https://doi.org/10.1000/test",
        )
    ]


def test_extract_sources_truncates_long_snippets() -> None:
    long_text = "x" * 500
    sources = PipelineService._extract_sources(
        [{"chunk_id": "a", "title": "T", "doi": "", "text": long_text, "score": 0.3}]
    )

    assert len(sources) == 1
    assert sources[0].snippet.endswith("...")
    assert len(sources[0].snippet) <= 320
