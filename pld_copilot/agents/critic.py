from __future__ import annotations

from pld_copilot.config import AppConfig
from pld_copilot.llm import LocalOpenAICompatibleClient
from pld_copilot.models import RetrievedChunk
from pld_copilot.prompts import CRITIC_PROMPT


class CriticAgent:
    def __init__(self, client: LocalOpenAICompatibleClient, config: AppConfig) -> None:
        self.client = client
        self.config = config

    def review(self, query: str, draft_answer: str, evidence: list[RetrievedChunk]) -> dict:
        evidence_summary = [
            {"doi": chunk.doi, "title": chunk.title, "text": chunk.text}
            for chunk in evidence
        ]
        user_prompt = (
            f"Question:\n{query}\n\n"
            f"Draft answer:\n{draft_answer}\n\n"
            f"Evidence:\n{evidence_summary}"
        )
        return self.client.chat_json(
            model=self.config.llm.critic_model,
            system_prompt=CRITIC_PROMPT,
            user_prompt=user_prompt,
        )
