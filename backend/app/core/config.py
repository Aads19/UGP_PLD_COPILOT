from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

from pld_copilot.config import (
    AppConfig,
    ChromaConfig,
    CorpusConfig,
    LLMConfig,
    PolicyConfig,
    RetrievalConfig,
)

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def _bool_from_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int_from_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    return int(raw)


def _float_from_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    return float(raw)


def _list_from_env(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


def _examples_from_env(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return [item.strip() for item in raw.split("|") if item.strip()]


@dataclass
class Settings:
    app_name: str
    app_env: str
    allowed_origins: list[str]
    api_rate_limit: int
    database_url: str
    pipeline_config: AppConfig


def _build_pipeline_config() -> AppConfig:
    return AppConfig(
        chroma=ChromaConfig(
            persist_directory=os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_store"),
            collection_name=os.getenv("CHROMA_COLLECTION_NAME", "pvd_docs"),
        ),
        corpus=CorpusConfig(
            csv_paths=[],
            text_column_priority=["text_chunk", "paragraph", "sentence"],
            metadata_defaults={
                "domain": "materials_science",
                "source_type": "chroma_bundle",
            },
        ),
        retrieval=RetrievalConfig(
            enabled=_bool_from_env("RETRIEVAL_ENABLED", True),
            top_k=_int_from_env("RETRIEVAL_TOP_K", 10),
            retry_top_k=_int_from_env("RETRIEVAL_RETRY_TOP_K", 20),
            min_relevance_passes=_int_from_env("RETRIEVAL_MIN_RELEVANCE_PASSES", 3),
        ),
        llm=LLMConfig(
            base_url=os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1"),
            api_key=os.getenv("GROQ_API_KEY", ""),
            router_model=os.getenv("LLM_ROUTER_MODEL", "llama-3.1-8b-instant"),
            rewrite_model=os.getenv("LLM_REWRITE_MODEL", "llama-3.1-8b-instant"),
            grader_model=os.getenv("LLM_GRADER_MODEL", "llama-3.1-8b-instant"),
            synthesis_model=os.getenv("LLM_SYNTHESIS_MODEL", "llama-3.1-70b-versatile"),
            critic_model=os.getenv("LLM_CRITIC_MODEL", "llama-3.1-8b-instant"),
            formatter_model=os.getenv("LLM_FORMATTER_MODEL", "llama-3.1-8b-instant"),
            router_base_url=os.getenv("LLM_ROUTER_BASE_URL") or None,
            router_api_key=os.getenv("LLM_ROUTER_API_KEY") or None,
            temperature=_float_from_env("LLM_TEMPERATURE", 0.1),
            timeout_seconds=_int_from_env("LLM_TIMEOUT_SECONDS", 90),
        ),
        policy=PolicyConfig(
            no_web=True,
            max_retry_rounds=_int_from_env("POLICY_MAX_RETRY_ROUNDS", 2),
            small_talk_examples=_examples_from_env(
                "POLICY_SMALL_TALK_EXAMPLES",
                ["hello", "how are you", "thanks", "tell me a joke"],
            ),
        ),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "UGP PLD Copilot API"),
        app_env=os.getenv("APP_ENV", "development"),
        allowed_origins=_list_from_env("ALLOWED_ORIGINS", ["http://localhost:3000"]),
        api_rate_limit=_int_from_env("API_RATE_LIMIT", 20),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./pld_copilot.db"),
        pipeline_config=_build_pipeline_config(),
    )
