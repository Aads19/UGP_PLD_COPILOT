from __future__ import annotations

from pathlib import Path

from pld_copilot.ingestion import ingest_corpus


def bootstrap_chroma_if_needed(config) -> dict[str, object]:
    if not config.retrieval.enabled:
        return {"bootstrapped": False, "reason": "retrieval_disabled"}

    try:
        import chromadb
    except ImportError:
        return {"bootstrapped": False, "reason": "chromadb_not_installed"}

    persist_path = Path(config.chroma.persist_directory)
    persist_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(persist_path))
    collection = client.get_or_create_collection(name=config.chroma.collection_name)

    if collection.count() > 0:
        return {
            "bootstrapped": False,
            "reason": "existing_collection",
            "count": collection.count(),
        }

    if not config.corpus.csv_paths:
        return {"bootstrapped": False, "reason": "no_corpus_paths"}

    available_paths = [path for path in config.corpus.csv_paths if Path(path).exists()]
    if not available_paths:
        return {"bootstrapped": False, "reason": "missing_bootstrap_csv"}

    config.corpus.csv_paths = available_paths
    ingested = ingest_corpus(config=config, reset=False)
    return {
        "bootstrapped": True,
        "reason": "ingested_from_csv",
        "count": ingested,
    }
