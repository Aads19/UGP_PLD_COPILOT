from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

from pld_copilot.config import AppConfig, ChromaConfig, CorpusConfig, LLMConfig, PolicyConfig, RetrievalConfig

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def _default_corpus_paths() -> list[str]:
    explicit = os.getenv("CSV_PATH")
    if explicit:
        return [explicit]

    repo_root = Path(__file__).resolve().parents[3]
    bundled_dataset = repo_root / "PLD CATEGORY FINAL DATASET.csv"
    if bundled_dataset.exists():
        return [str(bundled_dataset)]
    return []


def _database_url_from_env() -> str:
    explicit_url = os.getenv("DATABASE_URL")
    if explicit_url:
        return explicit_url

    raw_path = os.getenv("DATABASE_PATH", "./conversations.db")
    db_path = Path(raw_path)
    if db_path.is_absolute():
        return f"sqlite:///{db_path.as_posix()}"
    normalized = db_path.as_posix()
    if normalized.startswith("./"):
        return f"sqlite:///{normalized}"
    return f"sqlite:///./{normalized}"


def _allowed_origins_from_env() -> list[str]:
    explicit = os.getenv("ALLOWED_ORIGINS")
    if explicit:
        return [item.strip() for item in explicit.split(",") if item.strip()]

    origins = ["http://localhost:3000"]
    frontend_url = os.getenv("FRONTEND_URL")
    if frontend_url:
        origins.insert(0, frontend_url.strip())
    return origins


@dataclass
class Settings:
    app_name: str
    app_env: str
    allowed_origins: list[str]
    api_rate_limit: int
    database_url: str
    pipeline_config: AppConfig


def _build_pipeline_config() -> AppConfig:
    chroma_path = os.getenv("CHROMA_PATH") or os.getenv("CHROMA_PERSIST_DIRECTORY") or "./chroma_db"
    return AppConfig(
        chroma=ChromaConfig(
            persist_directory=chroma_path,
            collection_name=os.getenv("CHROMA_COLLECTION_NAME", "pvd_docs"),
        ),
        corpus=CorpusConfig(
            csv_paths=_default_corpus_paths(),
            text_column_priority=["text_chunk", "paragraph", "sentence", "text"],
            metadata_defaults={
                "domain": "materials_science",
                "source_type": "local_csv",
            },
        ),
        retrieval=RetrievalConfig(
            enabled=(os.getenv("RETRIEVAL_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}),
            top_k=int(os.getenv("RETRIEVAL_TOP_K", "3")),
            candidate_count=int(os.getenv("RETRIEVAL_CANDIDATE_COUNT", "9")),
        ),
        llm=LLMConfig(
            base_url=os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1"),
            api_key=os.getenv("GROQ_API_KEY", ""),
            router_model=os.getenv("LLM_ROUTER_MODEL", "llama-3.1-8b-instant"),
            rewrite_model=os.getenv("LLM_REWRITE_MODEL", "llama-3.1-8b-instant"),
            grader_model=os.getenv("LLM_GRADER_MODEL", "llama-3.1-8b-instant"),
            synthesis_model=os.getenv("LLM_SYNTHESIS_MODEL", "llama-3.1-8b-instant"),
            critic_model=os.getenv("LLM_CRITIC_MODEL", "llama-3.1-8b-instant"),
            formatter_model=os.getenv("LLM_FORMATTER_MODEL", "llama-3.1-8b-instant"),
            router_base_url=os.getenv("LLM_ROUTER_BASE_URL") or None,
            router_api_key=os.getenv("LLM_ROUTER_API_KEY") or None,
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.1")),
            timeout_seconds=int(os.getenv("LLM_TIMEOUT_SECONDS", "90")),
            gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            embedding_model_name=os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-small-en-v1.5"),
            reranker_model_name=os.getenv("RERANKER_MODEL_NAME", "cross-encoder/ms-marco-MiniLM-L-6-v2"),
            hyde_model=os.getenv("LLM_HYDE_MODEL") or os.getenv("LLM_REWRITE_MODEL", "llama-3.1-8b-instant"),
            chat_model=os.getenv("LLM_CHAT_MODEL") or os.getenv("LLM_ROUTER_MODEL", "llama-3.1-8b-instant"),
            paraphrase_model=os.getenv("LLM_PARAPHRASE_MODEL") or os.getenv("LLM_FORMATTER_MODEL", "llama-3.1-8b-instant"),
        ),
        policy=PolicyConfig(
            no_web=True,
            max_retry_rounds=0,
            small_talk_examples=["hello", "hi", "hey", "thanks", "thank you"],
        ),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "UGP PLD Copilot API"),
        app_env=os.getenv("APP_ENV", "development"),
        allowed_origins=_allowed_origins_from_env(),
        api_rate_limit=int(os.getenv("API_RATE_LIMIT", "20")),
        database_url=_database_url_from_env(),
        pipeline_config=_build_pipeline_config(),
    )
