from __future__ import annotations

import logging
import re

from pld_copilot.config import AppConfig
from pld_copilot.llm import LocalOpenAICompatibleClient
from pld_copilot.models import DirectorDecision
from pld_copilot.prompts import DIRECTOR_PROMPT

logger = logging.getLogger(__name__)

ALLOWED_TAGS = {"Background", "Synthesis", "Characterization", "Analysis"}


class DirectorAgent:
    def __init__(self, client: LocalOpenAICompatibleClient, config: AppConfig) -> None:
        self.client = client
        self.config = config

    def route(self, query: str) -> DirectorDecision:
        heuristics = self._heuristic_route(query)
        if not self.client.api_key:
            return heuristics

        user_prompt = (
            f"User query: {query}\n"
            f"Small talk examples: {self.config.policy.small_talk_examples}\n"
            "Classify the query and return JSON."
        )
        try:
            result = self.client.chat_json(
                model=self.config.llm.router_model,
                system_prompt=DIRECTOR_PROMPT,
                user_prompt=user_prompt,
                temperature=0,
                max_tokens=300,
            )
            decision = str(result.get("decision", heuristics.decision)).strip().lower()
            tags = [tag for tag in result.get("target_tags", []) if tag in ALLOWED_TAGS]
            if decision not in {"chat", "database"}:
                decision = heuristics.decision
            if decision == "database" and not tags:
                tags = heuristics.target_tags
            return DirectorDecision(
                decision=decision,
                reasoning=str(result.get("reasoning", heuristics.reasoning)).strip() or heuristics.reasoning,
                target_tags=tags,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Director agent failed; using heuristic fallback: %s", exc)
            return heuristics

    def _heuristic_route(self, query: str) -> DirectorDecision:
        stripped = query.strip()
        lowered = stripped.lower()

        if re.fullmatch(r"(hi|hello|hey|thanks|thank you|good morning|good evening)[!. ]*", lowered):
            return DirectorDecision(
                decision="chat",
                reasoning="Matched a conversational greeting/thanks pattern.",
                target_tags=[],
            )

        tags: list[str] = []
        keyword_groups = {
            "Synthesis": [
                "deposition",
                "growth",
                "temperature",
                "pressure",
                "fluence",
                "sputter",
                "sputtering",
                "pld",
                "laser",
                "substrate",
                "anneal",
                "fabrication",
            ],
            "Characterization": [
                "xrd",
                "sem",
                "tem",
                "afm",
                "raman",
                "xps",
                "eis",
                "morphology",
                "characterization",
                "rocking curve",
            ],
            "Analysis": [
                "performance",
                "conductivity",
                "impedance",
                "analysis",
                "effect",
                "influence",
                "results",
                "interpretation",
            ],
            "Background": [
                "what is",
                "why",
                "mechanism",
                "theory",
                "background",
                "principle",
                "history",
                "explain",
            ],
        }
        for tag, keywords in keyword_groups.items():
            if any(keyword in lowered for keyword in keywords):
                tags.append(tag)

        if not tags:
            tags = ["Background"]

        return DirectorDecision(
            decision="database",
            reasoning="Defaulted to database because the query appears scientific or technical.",
            target_tags=tags,
        )
