from __future__ import annotations

from pld_copilot.config import AppConfig
from pld_copilot.llm import LocalOpenAICompatibleClient
from pld_copilot.prompts import FORMATTER_PROMPT


class FormatterAgent:
    def __init__(self, client: LocalOpenAICompatibleClient, config: AppConfig) -> None:
        self.client = client
        self.config = config

    def format(self, answer_text: str) -> str:
        return self.client.chat(
            model=self.config.llm.formatter_model,
            system_prompt=FORMATTER_PROMPT,
            user_prompt=answer_text,
        ).strip()
