from __future__ import annotations

import logging

from pld_copilot.config import AppConfig
from pld_copilot.llm import LocalOpenAICompatibleClient
from pld_copilot.prompts import QUERY_EXPANDER_PROMPT

logger = logging.getLogger(__name__)


class QueryExpanderAgent:
    def __init__(self, client: LocalOpenAICompatibleClient, config: AppConfig) -> None:
        self.client = client
        self.config = config

    def expand(self, query: str, target_tags: list[str]) -> str:
        if not self.client.api_key:
            return query

        user_prompt = (
            f"Original question: {query}\n"
            f"Assigned tags: {target_tags}\n"
            "Generate the optimized retrieval query and return JSON."
        )
        try:
            result = self.client.chat_json(
                model=self.config.llm.rewrite_model,
                system_prompt=QUERY_EXPANDER_PROMPT,
                user_prompt=user_prompt,
                temperature=0.2,
                max_tokens=300,
            )
            optimized = str(result.get("optimized_query", "")).strip()
            return optimized or query
        except Exception as exc:  # noqa: BLE001
            logger.warning("Query expander JSON parse failed; retrying with plain text: %s", exc)
            try:
                optimized = self.client.chat(
                    model=self.config.llm.rewrite_model,
                    system_prompt=(
                        "Rewrite the user question into one dense academic retrieval query. "
                        "Return only the query text and nothing else."
                    ),
                    user_prompt=f"Original question: {query}\nAssigned tags: {target_tags}",
                    temperature=0.2,
                    max_tokens=220,
                ).strip()
                if optimized:
                    return optimized
            except Exception as retry_exc:  # noqa: BLE001
                logger.warning("Query expander plain-text retry failed; using raw query: %s", retry_exc)
            return query
