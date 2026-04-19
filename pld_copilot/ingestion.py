from __future__ import annotations

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

from pld_copilot.config import AppConfig


def ingest_corpus(config: AppConfig, reset: bool = False) -> int:
    if chromadb is None:
        raise RuntimeError("chromadb is not installed. Install dependencies and enable retrieval before ingesting.")
    if pd is None:
        raise RuntimeError("pandas is not installed. Install dependencies before ingesting.")

    persist_path = Path(config.chroma.persist_directory)
    if reset and persist_path.exists():
        rmtree(persist_path)

    client = chromadb.PersistentClient(path=str(persist_path))
    collection = client.get_or_create_collection(name=config.chroma.collection_name)

    records = _load_records(config)
    if not records:
        raise ValueError("No records found for ingestion.")

    ids = [record["id"] for record in records]
    documents = [record["text"] for record in records]
    metadatas = [record["metadata"] for record in records]

    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
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
            abstract = str(row.get("abstract", "")).strip()

            metadata = {
                "doi": doi,
                "title": title,
                "abstract": abstract,
                "source_file": source_name,
                "text_column": text_column,
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
