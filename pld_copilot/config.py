from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ChromaConfig:
    persist_directory: str
    collection_name: str


@dataclass
class CorpusConfig:
    csv_paths: list[str]
    text_column_priority: list[str]
    metadata_defaults: dict[str, str] = field(default_factory=dict)


@dataclass
class RetrievalConfig:
    enabled: bool = False
    top_k: int = 10
    retry_top_k: int = 20
    min_relevance_passes: int = 3


@dataclass
class LLMConfig:
    base_url: str
    api_key: str
    router_model: str
    rewrite_model: str
    grader_model: str
    synthesis_model: str
    critic_model: str
    formatter_model: str
    router_base_url: str | None = None
    router_api_key: str | None = None
    temperature: float = 0.1
    timeout_seconds: int = 90


@dataclass
class PolicyConfig:
    no_web: bool = True
    max_retry_rounds: int = 2
    small_talk_examples: list[str] = field(default_factory=list)


@dataclass
class AppConfig:
    chroma: ChromaConfig
    corpus: CorpusConfig
    retrieval: RetrievalConfig
    llm: LLMConfig
    policy: PolicyConfig


def _resolve_paths(base_dir: Path, csv_paths: list[str]) -> list[str]:
    resolved = []
    for raw_path in csv_paths:
        path = Path(raw_path)
        if not path.is_absolute():
            path = (base_dir / path).resolve()
        resolved.append(str(path))
    return resolved


def load_config(path: Path) -> AppConfig:
    with path.open("r", encoding="utf-8") as handle:
        raw: dict[str, Any] = yaml.safe_load(handle)

    base_dir = path.parent.resolve()
    corpus_cfg = raw["corpus"]
    corpus_cfg["csv_paths"] = _resolve_paths(base_dir, corpus_cfg.get("csv_paths", []))

    chroma_cfg = raw["chroma"]
    chroma_persist = Path(chroma_cfg["persist_directory"])
    if not chroma_persist.is_absolute():
        chroma_cfg["persist_directory"] = str((base_dir / chroma_persist).resolve())

    return AppConfig(
        chroma=ChromaConfig(**chroma_cfg),
        corpus=CorpusConfig(**corpus_cfg),
        retrieval=RetrievalConfig(**raw["retrieval"]),
        llm=LLMConfig(**raw["llm"]),
        policy=PolicyConfig(**raw["policy"]),
    )
