from __future__ import annotations

from pld_copilot.config import AppConfig
from pld_copilot.llm import LocalOpenAICompatibleClient
from pld_copilot.prompts import REWRITER_PROMPT


class QueryRewriterAgent:
    def __init__(self, client: LocalOpenAICompatibleClient, config: AppConfig) -> None:
        self.client = client
        self.config = config

    def rewrite(self, query: str) -> str:
        return self.client.chat(
            model=self.config.llm.rewrite_model,
            system_prompt=REWRITER_PROMPT,
            user_prompt=f"Original user question:\n{query}",
        ).strip()
