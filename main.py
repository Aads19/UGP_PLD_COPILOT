from __future__ import annotations

import argparse
from pathlib import Path

from pld_copilot.config import load_config
from pld_copilot.ingestion import ingest_corpus
from pld_copilot.pipeline import PLDCopilotPipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PLD copilot agentic framework")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser("ingest", help="Ingest local CSV data into ChromaDB")
    ingest_parser.add_argument("--config", required=True, help="Path to YAML config")
    ingest_parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete and rebuild the configured Chroma collection",
    )

    ask_parser = subparsers.add_parser("ask", help="Ask the PLD copilot a question")
    ask_parser.add_argument("--config", required=True, help="Path to YAML config")
    ask_parser.add_argument("--query", required=True, help="User query")

    return parser


def run_ingest(config_path: str, reset: bool) -> None:
    config = load_config(Path(config_path))
    if not config.retrieval.enabled:
        print("Retrieval is disabled in the config. Set retrieval.enabled: true before ingesting.")
        return
    count = ingest_corpus(config=config, reset=reset)
    print(f"Ingested {count} chunks into collection '{config.chroma.collection_name}'.")


def run_ask(config_path: str, query: str) -> None:
    config = load_config(Path(config_path))
    pipeline = PLDCopilotPipeline.from_config(config)
    result = pipeline.run(query)

    print("\n=== ROUTE ===")
    print(result.route)
    print("\n=== ANSWER ===")
    print(result.answer_markdown)

    if result.debug:
        print("\n=== DEBUG ===")
        for key, value in result.debug.items():
            print(f"{key}: {value}")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "ingest":
        run_ingest(config_path=args.config, reset=args.reset)
        return

    if args.command == "ask":
        run_ask(config_path=args.config, query=args.query)
        return

    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
