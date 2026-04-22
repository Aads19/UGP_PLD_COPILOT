from __future__ import annotations

import json
from pathlib import Path
from shutil import rmtree
from typing import Any

try:
    import chromadb
except ImportError:
    chromadb = None

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

try:
    import torch
except ImportError:
    torch = None

from pld_copilot.config import AppConfig

EMBED_BATCH_SIZE = 256
UPSERT_BATCH_SIZE = 1000


def ingest_corpus(config: AppConfig, reset: bool = False) -> int:
    if chromadb is None:
        raise RuntimeError("chromadb is not installed. Install dependencies before ingesting.")
    if pd is None:
        raise RuntimeError("pandas is not installed. Install dependencies before ingesting.")
    if SentenceTransformer is None:
        raise RuntimeError("sentence-transformers is not installed. Install dependencies before ingesting.")

    persist_path = Path(config.chroma.persist_directory)
    if reset and persist_path.exists():
        rmtree(persist_path)

    persist_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(persist_path))

    try:
        client.delete_collection(config.chroma.collection_name)
    except Exception:
        pass

    collection = client.get_or_create_collection(name=config.chroma.collection_name)

    records = _load_records(config)
    if not records:
        raise ValueError("No records found for ingestion.")

    device = "cuda" if torch is not None and torch.cuda.is_available() else "cpu"
    embedder = SentenceTransformer(config.llm.embedding_model_name, device=device)

    texts = [record["text"] for record in records]
    embeddings = embedder.encode(
        texts,
        batch_size=EMBED_BATCH_SIZE,
        normalize_embeddings=True,
        show_progress_bar=True,
    )

    for start in range(0, len(records), UPSERT_BATCH_SIZE):
        end = start + UPSERT_BATCH_SIZE
        batch = records[start:end]
        collection.upsert(
            ids=[record["id"] for record in batch],
            documents=[record["text"] for record in batch],
            metadatas=[record["metadata"] for record in batch],
            embeddings=embeddings[start:end].tolist(),
        )

    return len(records)


def _load_records(config: AppConfig) -> list[dict[str, Any]]:
    if pd is None:
        raise RuntimeError("pandas is not installed. Install dependencies before loading records.")

    records: list[dict[str, Any]] = []

    for csv_path in config.corpus.csv_paths:
        source_name = Path(csv_path).stem
        frame = pd.read_csv(csv_path)
        text_column = _pick_text_column(frame.columns.tolist(), config.corpus.text_column_priority)

        for row_index, row in frame.iterrows():
            text = str(row.get(text_column, "")).strip()
            if not text:
                continue

            doi = str(row.get("doi", "")).strip()
            title = str(row.get("title", "")).strip()
            chunk_idx = int(row.get("chunk_start_idx", row.get("chunk_idx", row_index)) or row_index)
            chunk_tags = _parse_tags(row.get("tags", "[]"))

            metadata = {
                "doi": doi,
                "title": title,
                "chunk_idx": chunk_idx,
                "source_file": source_name,
                "text_column": text_column,
                "is_Background": bool("Background" in chunk_tags),
                "is_Synthesis": bool("Synthesis" in chunk_tags),
                "is_Characterization": bool("Characterization" in chunk_tags),
                "is_Analysis": bool("Analysis" in chunk_tags),
                **config.corpus.metadata_defaults,
            }
            records.append(
                {
                    "id": f"{source_name}-{row_index}",
                    "text": text,
                    "metadata": _normalize_metadata(metadata),
                }
            )

    return records


def _parse_tags(raw_value: Any) -> list[str]:
    raw = str(raw_value or "[]").strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            tags = parsed.get("tags", [])
        else:
            tags = parsed
        if isinstance(tags, list):
            return [str(item) for item in tags]
    except Exception:
        return []
    return []


def _pick_text_column(columns: list[str], priority: list[str]) -> str:
    lower_map = {column.lower(): column for column in columns}
    for candidate in priority:
        if candidate.lower() in lower_map:
            return lower_map[candidate.lower()]
    raise ValueError(f"No supported text column found. Columns seen: {columns}")


def _normalize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            normalized[key] = value
        else:
            normalized[key] = str(value)
    return normalized
