from __future__ import annotations

from pld_copilot.config import AppConfig
from pld_copilot.llm import LocalOpenAICompatibleClient
from pld_copilot.models import GradedChunk, RetrievedChunk
from pld_copilot.prompts import GRADER_PROMPT


class DocumentGraderAgent:
    def __init__(self, client: LocalOpenAICompatibleClient, config: AppConfig) -> None:
        self.client = client
        self.config = config

    def grade(self, query: str, chunks: list[RetrievedChunk]) -> list[GradedChunk]:
        graded: list[GradedChunk] = []
        for chunk in chunks:
            user_prompt = (
                f"Question:\n{query}\n\n"
                f"Chunk title: {chunk.title}\n"
                f"Chunk DOI: {chunk.doi}\n"
                f"Chunk text:\n{chunk.text}"
            )
            result = self.client.chat_json(
                model=self.config.llm.grader_model,
                system_prompt=GRADER_PROMPT,
                user_prompt=user_prompt,
            )
            graded.append(
                GradedChunk(
                    chunk=chunk,
                    relevant=bool(result["relevant"]),
                    rationale=result["rationale"],
                )
            )
        return graded
