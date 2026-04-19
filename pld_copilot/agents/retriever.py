from __future__ import annotations

from typing import Any

try:
    import chromadb
except ImportError:
    chromadb = None

from pld_copilot.config import AppConfig
from pld_copilot.models import RetrievedChunk


class DataEngineerAgent:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.enabled = bool(config.retrieval.enabled)
        self.available = self.enabled and chromadb is not None
        self.client = None
        self.collection = None

        if self.available:
            self.client = chromadb.PersistentClient(path=config.chroma.persist_directory)
            self.collection = self.client.get_or_create_collection(name=config.chroma.collection_name)

    def retrieve(
        self,
        rewritten_query: str,
        metadata_filters: dict[str, Any] | None = None,
        top_k: int | None = None,
    ) -> list[RetrievedChunk]:
        if not self.available or self.collection is None:
            return []

        query_kwargs: dict[str, Any] = {
            "query_texts": [rewritten_query],
            "n_results": top_k or self.config.retrieval.top_k,
        }
        where = metadata_filters or {}
        if where:
            query_kwargs["where"] = where

        results = self.collection.query(**query_kwargs)

        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        chunks: list[RetrievedChunk] = []
        for idx, chunk_id in enumerate(ids):
            metadata = metadatas[idx] or {}
            chunks.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    text=documents[idx],
                    doi=str(metadata.get("doi", "")),
                    title=str(metadata.get("title", "")),
                    metadata=metadata,
                    score=distances[idx] if idx < len(distances) else None,
                )
            )
        return chunks

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "chromadb_installed": chromadb is not None,
            "available": self.available,
            "collection_name": self.config.chroma.collection_name,
        }
