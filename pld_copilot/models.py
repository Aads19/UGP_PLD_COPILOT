from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RouteDecision:
    route: str
    reason: str
    metadata_filters: dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievedChunk:
    chunk_id: str
    text: str
    doi: str
    title: str
    metadata: dict[str, Any]
    score: float | None = None


@dataclass
class GradedChunk:
    chunk: RetrievedChunk
    relevant: bool
    rationale: str


@dataclass
class PipelineResult:
    route: str
    answer_markdown: str
    citations: list[str]
    debug: dict[str, Any] = field(default_factory=dict)
