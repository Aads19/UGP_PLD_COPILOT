from __future__ import annotations

from pld_copilot.config import AppConfig
from pld_copilot.llm import LocalOpenAICompatibleClient
from pld_copilot.models import RouteDecision
from pld_copilot.prompts import DIRECTOR_PROMPT


class DirectorAgent:
    def __init__(
        self,
        default_client: LocalOpenAICompatibleClient,
        config: AppConfig,
    ) -> None:
        router_base_url = config.llm.router_base_url or config.llm.base_url
        router_api_key = config.llm.router_api_key or config.llm.api_key
        self.client = LocalOpenAICompatibleClient(
            base_url=router_base_url,
            api_key=router_api_key,
            temperature=config.llm.temperature,
            timeout_seconds=config.llm.timeout_seconds,
        )
        self.default_client = default_client
        self.config = config

    def route(self, query: str) -> RouteDecision:
        user_prompt = (
            f"User query: {query}\n"
            f"Small talk examples: {self.config.policy.small_talk_examples}\n"
            "Classify and return JSON."
        )
        result = self.client.chat_json(
            model=self.config.llm.router_model,
            system_prompt=DIRECTOR_PROMPT,
            user_prompt=user_prompt,
        )
        return RouteDecision(
            route=result["route"],
            reason=result["reason"],
            metadata_filters=result.get("metadata_filters", {}),
        )
