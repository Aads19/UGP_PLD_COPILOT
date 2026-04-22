from __future__ import annotations

import logging

try:
    import google.generativeai as genai
except ImportError:
    genai = None

from pld_copilot.config import AppConfig
from pld_copilot.models import RetrievedChunk
from pld_copilot.prompts import ANSWER_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class FinalAnswerAgent:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._configured = False

    def warmup(self) -> None:
        self._configure()

    def answer(self, query: str, chunks: list[RetrievedChunk]) -> str:
        if not chunks:
            return "I could not find relevant evidence in the indexed PLD corpus to answer that question."

        prompt = build_llm_context(query, chunks)
        fallback = _fallback_answer(query, chunks)

        if genai is None or not self.config.llm.gemini_api_key:
            return fallback

        model_names = [self.config.llm.gemini_model]
        if self.config.llm.gemini_model != "gemini-flash-latest":
            model_names.append("gemini-flash-latest")

        for model_name in model_names:
            try:
                self._configure()
                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=ANSWER_SYSTEM_PROMPT,
                )
                response = model.generate_content(
                    prompt,
                    generation_config=genai.GenerationConfig(temperature=0.2),
                )
                text = getattr(response, "text", "") or ""
                if text.strip():
                    return text.strip()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Gemini answer generation failed for %s: %s", model_name, exc)

        return fallback

    def _configure(self) -> None:
        if self._configured or genai is None or not self.config.llm.gemini_api_key:
            return
        genai.configure(api_key=self.config.llm.gemini_api_key)
        self._configured = True


def build_llm_context(query: str, chunks: list[RetrievedChunk]) -> str:
    evidence_blocks = []
    for index, chunk in enumerate(chunks, start=1):
        evidence_blocks.append(
            "\n".join(
                [
                    f"Chunk {index}",
                    f"Title: {chunk.title}",
                    f"DOI: {chunk.doi}",
                    f"Chunk Index: {chunk.chunk_idx}",
                    f"Text: {chunk.text}",
                ]
            )
        )

    return (
        f"Question:\n{query}\n\n"
        "Evidence Chunks:\n"
        + "\n\n".join(evidence_blocks)
    )


def _fallback_answer(query: str, chunks: list[RetrievedChunk]) -> str:
    evidence_lines = []
    for index, chunk in enumerate(chunks, start=1):
        snippet = chunk.text.strip()
        if len(snippet) > 320:
            snippet = snippet[:317].rstrip() + "..."
        evidence_lines.append(f"[Chunk {index}] {snippet}")

    return "\n\n".join(
        [
            "I found relevant evidence in the indexed corpus, but the final answer generator is unavailable right now.",
            "The most relevant retrieved passages are shown below for direct inspection:",
            *evidence_lines,
        ]
    )
