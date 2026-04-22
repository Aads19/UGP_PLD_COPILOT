from __future__ import annotations

import logging

from pld_copilot.config import AppConfig
from pld_copilot.llm import LocalOpenAICompatibleClient
from pld_copilot.prompts import HYDE_PROMPT

logger = logging.getLogger(__name__)


class HyDEAgent:
    def __init__(self, client: LocalOpenAICompatibleClient, config: AppConfig) -> None:
        self.client = client
        self.config = config

    def generate(self, query: str, target_tags: list[str]) -> str:
        if not self.client.api_key:
            return query

        user_prompt = (
            f"Original question: {query}\n"
            f"Assigned tags: {target_tags}\n"
            "Write the hypothetical document paragraph and return JSON."
        )
        model = self.config.llm.hyde_model or self.config.llm.rewrite_model
        try:
            result = self.client.chat_json(
                model=model,
                system_prompt=HYDE_PROMPT,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=500,
            )
            hypothetical_document = str(result.get("hypothetical_document", "")).strip()
            return hypothetical_document or query
        except Exception as exc:  # noqa: BLE001
            logger.warning("HyDE JSON parse failed; retrying with plain text: %s", exc)
            try:
                hypothetical_document = self.client.chat(
                    model=model,
                    system_prompt=(
                        "Write one dense academic paragraph for retrieval over PVD literature. "
                        "Return only the paragraph text."
                    ),
                    user_prompt=f"Original question: {query}\nAssigned tags: {target_tags}",
                    temperature=0.3,
                    max_tokens=420,
                ).strip()
                if hypothetical_document:
                    return hypothetical_document
            except Exception as retry_exc:  # noqa: BLE001
                logger.warning("HyDE plain-text retry failed; using the expanded query: %s", retry_exc)
            return query
