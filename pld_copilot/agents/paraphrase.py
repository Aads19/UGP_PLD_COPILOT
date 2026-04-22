from __future__ import annotations

import logging
import re

from pld_copilot.config import AppConfig
from pld_copilot.llm import LocalOpenAICompatibleClient
from pld_copilot.models import RetrievedChunk
from pld_copilot.prompts import PARAPHRASE_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

CHUNK_CITATION_PATTERN = re.compile(r"\[Chunk\s+(\d+)\]")


class ParaphraseAgent:
    def __init__(self, client: LocalOpenAICompatibleClient, config: AppConfig) -> None:
        self.client = client
        self.config = config

    def paraphrase(self, query: str, draft_answer: str, chunks: list[RetrievedChunk]) -> str:
        cleaned_draft = draft_answer.strip()
        if not cleaned_draft:
            return ""

        cited_indices = _extract_cited_indices(cleaned_draft, len(chunks))
        draft_without_inline_markers = CHUNK_CITATION_PATTERN.sub("", cleaned_draft)
        draft_without_inline_markers = re.sub(r"\s{2,}", " ", draft_without_inline_markers).strip()

        paraphrased_body = draft_without_inline_markers
        model = self.config.llm.paraphrase_model or self.config.llm.formatter_model
        if self.client.api_key:
            try:
                paraphrased_body = self.client.chat(
                    model=model,
                    system_prompt=PARAPHRASE_SYSTEM_PROMPT,
                    user_prompt=(
                        f"Original question:\n{query}\n\n"
                        f"Draft answer:\n{draft_without_inline_markers}"
                    ),
                    temperature=0.4,
                    max_tokens=900,
                ).strip() or draft_without_inline_markers
            except Exception as exc:  # noqa: BLE001
                logger.warning("Paraphrasing failed; using the draft answer body: %s", exc)

        citations_section = _build_citations_section(cited_indices, chunks)
        if citations_section:
            return f"{paraphrased_body}\n\n{citations_section}".strip()
        return paraphrased_body


def _extract_cited_indices(answer: str, chunk_count: int) -> list[int]:
    found = []
    for match in CHUNK_CITATION_PATTERN.findall(answer):
        try:
            index = int(match)
        except ValueError:
            continue
        if 1 <= index <= chunk_count and index not in found:
            found.append(index)
    if found:
        return found
    return list(range(1, chunk_count + 1))


def _build_citations_section(cited_indices: list[int], chunks: list[RetrievedChunk]) -> str:
    lines = ["Citations", "---------"]
    for index in cited_indices:
        chunk = chunks[index - 1]
        title = chunk.title or f"Retrieved paper {index}"
        if chunk.doi:
            lines.append(f"{index}. {title} — DOI: {chunk.doi}")
        else:
            lines.append(f"{index}. {title}")
    return "\n".join(lines)
