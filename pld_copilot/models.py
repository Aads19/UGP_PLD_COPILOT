from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DirectorDecision:
    decision: str
    reasoning: str
    target_tags: list[str] = field(default_factory=list)


@dataclass
class RetrievedChunk:
    chunk_id: str
    text: str
    doi: str
    title: str
    chunk_idx: int
    metadata: dict[str, Any] = field(default_factory=dict)
    score: float | None = None
    origin: str = ""


@dataclass
class PipelineResult:
    route: str
    answer_markdown: str
    sources: list[RetrievedChunk] = field(default_factory=list)
    debug: dict[str, Any] = field(default_factory=dict)
