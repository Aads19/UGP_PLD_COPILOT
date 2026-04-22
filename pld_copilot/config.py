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
    enabled: bool = True
    top_k: int = 3
    candidate_count: int = 9


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
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    embedding_model_name: str = "BAAI/bge-small-en-v1.5"
    reranker_model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    hyde_model: str | None = None
    chat_model: str | None = None
    paraphrase_model: str | None = None


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

    llm_cfg = raw["llm"]
    llm_cfg.setdefault("gemini_api_key", "")
    llm_cfg.setdefault("gemini_model", "gemini-2.0-flash")
    llm_cfg.setdefault("embedding_model_name", "BAAI/bge-small-en-v1.5")
    llm_cfg.setdefault("reranker_model_name", "cross-encoder/ms-marco-MiniLM-L-6-v2")
    llm_cfg.setdefault("hyde_model", llm_cfg.get("rewrite_model"))
    llm_cfg.setdefault("chat_model", llm_cfg.get("router_model"))
    llm_cfg.setdefault("paraphrase_model", llm_cfg.get("formatter_model"))

    retrieval_cfg = raw["retrieval"]
    retrieval_cfg.setdefault("enabled", True)
    retrieval_cfg.setdefault("top_k", 3)
    retrieval_cfg.setdefault("candidate_count", 9)

    return AppConfig(
        chroma=ChromaConfig(**chroma_cfg),
        corpus=CorpusConfig(**corpus_cfg),
        retrieval=RetrievalConfig(**retrieval_cfg),
        llm=LLMConfig(**llm_cfg),
        policy=PolicyConfig(**raw["policy"]),
    )
