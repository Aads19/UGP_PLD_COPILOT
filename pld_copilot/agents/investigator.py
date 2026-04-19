from __future__ import annotations

from pld_copilot.config import AppConfig
from pld_copilot.llm import LocalOpenAICompatibleClient
from pld_copilot.models import RetrievedChunk
from pld_copilot.prompts import SYNTHESIS_PROMPT


class PrincipalInvestigatorAgent:
    def __init__(self, client: LocalOpenAICompatibleClient, config: AppConfig) -> None:
        self.client = client
        self.config = config

    def synthesize(self, query: str, evidence: list[RetrievedChunk]) -> str:
        evidence_blocks = []
        for idx, chunk in enumerate(evidence, start=1):
            evidence_blocks.append(
                "\n".join(
                    [
                        f"Evidence {idx}",
                        f"Title: {chunk.title}",
                        f"DOI: {chunk.doi}",
                        f"Text: {chunk.text}",
                    ]
                )
            )

        user_prompt = (
            f"Question:\n{query}\n\n"
            "Evidence:\n"
            + "\n\n".join(evidence_blocks)
        )
        return self.client.chat(
            model=self.config.llm.synthesis_model,
            system_prompt=SYNTHESIS_PROMPT,
            user_prompt=user_prompt,
        ).strip()
