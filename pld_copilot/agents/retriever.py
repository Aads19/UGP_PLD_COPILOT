from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

try:
    import chromadb
except ImportError:
    chromadb = None

try:
    from sentence_transformers import CrossEncoder, SentenceTransformer
except ImportError:
    CrossEncoder = None
    SentenceTransformer = None

try:
    import torch
except ImportError:
    torch = None

from pld_copilot.config import AppConfig
from pld_copilot.models import RetrievedChunk

logger = logging.getLogger(__name__)

TAG_TO_FIELD = {
    "Background": "is_Background",
    "Synthesis": "is_Synthesis",
    "Characterization": "is_Characterization",
    "Analysis": "is_Analysis",
}


def _build_tag_filter(target_tags: list[str]) -> dict[str, Any] | None:
    clauses = []
    for tag in target_tags:
        field_name = TAG_TO_FIELD.get(tag)
        if field_name:
            clauses.append({field_name: {"$eq": True}})

    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$or": clauses}


class DataEngineerAgent:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.enabled = bool(config.retrieval.enabled)
        self._client = None
        self._collection = None
        self._embedder = None
        self._cross_encoder = None

    @property
    def available(self) -> bool:
        return (
            self.enabled
            and chromadb is not None
            and SentenceTransformer is not None
            and CrossEncoder is not None
        )

    def warmup(self) -> None:
        if not self.available:
            return
        self.get_collection()
        self.get_embedder()
        self.get_cross_encoder()

    def get_collection(self):
        if chromadb is None or not self.enabled:
            return None
        if self._collection is None:
            persist_directory = Path(self.config.chroma.persist_directory)
            if not persist_directory.exists():
                logger.error("Chroma persist directory not found: %s", persist_directory)
                return None
            self._client = chromadb.PersistentClient(path=str(persist_directory))
            try:
                self._collection = self._client.get_collection(name=self.config.chroma.collection_name)
            except Exception as exc:  # noqa: BLE001
                logger.error("Unable to open Chroma collection '%s': %s", self.config.chroma.collection_name, exc)
                return None
        return self._collection

    def get_embedder(self):
        if SentenceTransformer is None:
            return None
        if self._embedder is None:
            device = "cuda" if torch is not None and torch.cuda.is_available() else "cpu"
            self._embedder = SentenceTransformer(
                self.config.llm.embedding_model_name,
                device=device,
            )
        return self._embedder

    def get_cross_encoder(self):
        if CrossEncoder is None:
            return None
        if self._cross_encoder is None:
            device = "cuda" if torch is not None and torch.cuda.is_available() else "cpu"
            self._cross_encoder = CrossEncoder(
                self.config.llm.reranker_model_name,
                device=device,
            )
        return self._cross_encoder

    def retrieve_from_expanded_query(self, expanded_query: str, target_tags: list[str]) -> list[RetrievedChunk]:
        chunks = self._query_collection(expanded_query, target_tags, origin="expanded_query")
        return self._rerank(expanded_query, chunks, top_k=self.config.retrieval.top_k)

    def retrieve_from_hyde(self, hyde_document: str, target_tags: list[str]) -> list[RetrievedChunk]:
        chunks = self._query_collection(hyde_document, target_tags, origin="hyde_document")
        return self._rerank(hyde_document, chunks, top_k=self.config.retrieval.top_k)

    def combine_and_rerank_chunks(
        self,
        original_query: str,
        hyde_chunks: list[RetrievedChunk],
        expanded_query_chunks: list[RetrievedChunk],
    ) -> list[RetrievedChunk]:
        deduped: dict[str, RetrievedChunk] = {}
        for chunk in hyde_chunks + expanded_query_chunks:
            current = deduped.get(chunk.chunk_id)
            if current is None or (chunk.score or float("-inf")) > (current.score or float("-inf")):
                deduped[chunk.chunk_id] = chunk

        return self._rerank(
            original_query,
            list(deduped.values()),
            top_k=self.config.retrieval.top_k,
        )

    def status(self) -> dict[str, Any]:
        collection = self.get_collection()
        return {
            "enabled": self.enabled,
            "chromadb_installed": chromadb is not None,
            "sentence_transformers_installed": SentenceTransformer is not None and CrossEncoder is not None,
            "available": self.available and collection is not None,
            "collection_name": self.config.chroma.collection_name,
            "persist_directory": self.config.chroma.persist_directory,
            "collection_count": collection.count() if collection is not None else 0,
        }

    def _query_collection(
        self,
        query_text: str,
        target_tags: list[str],
        *,
        origin: str,
    ) -> list[RetrievedChunk]:
        collection = self.get_collection()
        embedder = self.get_embedder()
        if collection is None or embedder is None:
            return []

        query_embedding = embedder.encode(
            [query_text],
            normalize_embeddings=True,
        )[0].tolist()
        query_kwargs: dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": self.config.retrieval.candidate_count,
            "include": ["documents", "metadatas", "distances"],
        }
        where = _build_tag_filter(target_tags)
        if where:
            query_kwargs["where"] = where

        try:
            results = collection.query(**query_kwargs)
        except Exception as exc:  # noqa: BLE001
            logger.error("Chroma query failed: %s", exc)
            return []

        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        chunks: list[RetrievedChunk] = []
        for idx, chunk_id in enumerate(ids):
            metadata = metadatas[idx] or {}
            chunks.append(
                RetrievedChunk(
                    chunk_id=str(chunk_id),
                    text=str(documents[idx]),
                    doi=str(metadata.get("doi", "")),
                    title=str(metadata.get("title", "")),
                    chunk_idx=int(metadata.get("chunk_idx", 0) or 0),
                    metadata=metadata,
                    score=_distance_to_score(distances[idx] if idx < len(distances) else None),
                    origin=origin,
                )
            )
        return chunks

    def _rerank(
        self,
        reference_text: str,
        chunks: list[RetrievedChunk],
        *,
        top_k: int,
    ) -> list[RetrievedChunk]:
        if not chunks:
            return []

        reranker = self.get_cross_encoder()
        if reranker is None:
            return sorted(chunks, key=lambda item: item.score or float("-inf"), reverse=True)[:top_k]

        pairs = [[reference_text, chunk.text] for chunk in chunks]
        try:
            scores = reranker.predict(pairs)
        except Exception as exc:  # noqa: BLE001
            logger.error("Cross-encoder reranking failed: %s", exc)
            return sorted(chunks, key=lambda item: item.score or float("-inf"), reverse=True)[:top_k]

        for chunk, score in zip(chunks, scores):
            chunk.score = float(score)
        return sorted(chunks, key=lambda item: item.score or float("-inf"), reverse=True)[:top_k]


def _distance_to_score(distance: Any) -> float | None:
    if distance is None:
        return None
    try:
        return 1.0 / (1.0 + float(distance))
    except (TypeError, ValueError):
        return None
