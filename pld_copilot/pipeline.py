from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any, Callable, TypeVar

from pld_copilot.agents.answer import FinalAnswerAgent
from pld_copilot.agents.director import DirectorAgent
from pld_copilot.agents.expander import QueryExpanderAgent
from pld_copilot.agents.hyde import HyDEAgent
from pld_copilot.agents.paraphrase import ParaphraseAgent
from pld_copilot.agents.retriever import DataEngineerAgent
from pld_copilot.config import AppConfig
from pld_copilot.llm import LocalOpenAICompatibleClient
from pld_copilot.models import DirectorDecision, PipelineResult, RetrievedChunk
from pld_copilot.prompts import CHAT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

T = TypeVar("T")


class PLDCopilotPipeline:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.groq_client = LocalOpenAICompatibleClient(
            base_url=config.llm.base_url,
            api_key=config.llm.api_key,
            temperature=config.llm.temperature,
            timeout_seconds=config.llm.timeout_seconds,
        )
        self.director = DirectorAgent(self.groq_client, config)
        self.expander = QueryExpanderAgent(self.groq_client, config)
        self.hyde = HyDEAgent(self.groq_client, config)
        self.retriever = DataEngineerAgent(config)
        self.answer_agent = FinalAnswerAgent(config)
        self.paraphrase_agent = ParaphraseAgent(self.groq_client, config)

    @classmethod
    def from_config(cls, config: AppConfig) -> "PLDCopilotPipeline":
        return cls(config)

    def warmup(self) -> None:
        self.retriever.warmup()
        self.answer_agent.warmup()

    def run(self, query: str) -> PipelineResult:
        debug: dict[str, Any] = {"original_query": query}

        director_decision = self._stage(
            "chief_director",
            lambda: self.director.route(query),
            fallback=self.director._heuristic_route(query),  # noqa: SLF001
        )
        debug["director"] = asdict(director_decision)

        if director_decision.decision == "chat":
            answer = self._stage(
                "chat_reply",
                lambda: self._chat_reply(query),
                fallback="Hello! How can I help you with your PVD research today?",
            )
            return PipelineResult(route="chat", answer_markdown=answer, sources=[], debug=debug)

        expanded_query = self._stage(
            "query_expander",
            lambda: self.expander.expand(query, director_decision.target_tags),
            fallback=query,
        )
        debug["expanded_query"] = expanded_query

        hyde_document = self._stage(
            "hyde_generator",
            lambda: self.hyde.generate(query, director_decision.target_tags),
            fallback=expanded_query,
        )
        debug["hyde_document"] = hyde_document

        expanded_query_chunks = self._stage(
            "query_expander_retriever_node",
            lambda: self.retriever.retrieve_from_expanded_query(expanded_query, director_decision.target_tags),
            fallback=[],
        )
        hyde_chunks = self._stage(
            "retriever_node",
            lambda: self.retriever.retrieve_from_hyde(hyde_document, director_decision.target_tags),
            fallback=[],
        )
        debug["expanded_query_chunks"] = [asdict(chunk) for chunk in expanded_query_chunks]
        debug["hyde_chunks"] = [asdict(chunk) for chunk in hyde_chunks]

        final_retrieved_chunks = self._stage(
            "hybrid_retriever_node",
            lambda: self.retriever.combine_and_rerank_chunks(query, hyde_chunks, expanded_query_chunks),
            fallback=expanded_query_chunks[: self.config.retrieval.top_k] or hyde_chunks[: self.config.retrieval.top_k],
        )
        debug["final_retrieved_chunks"] = [asdict(chunk) for chunk in final_retrieved_chunks]
        debug["retriever_status"] = self.retriever.status()

        if not final_retrieved_chunks:
            return PipelineResult(
                route="database",
                answer_markdown=(
                    "I could not find relevant chunks in the indexed PVD literature database for that question."
                ),
                sources=[],
                debug=debug,
            )

        draft_answer = self._stage(
            "final_answer_node",
            lambda: self.answer_agent.answer(query, final_retrieved_chunks),
            fallback=self._fallback_grounded_answer(final_retrieved_chunks),
        )
        debug["draft_answer"] = draft_answer

        final_answer = self._stage(
            "final_paraphrase_node",
            lambda: self.paraphrase_agent.paraphrase(query, draft_answer, final_retrieved_chunks),
            fallback=draft_answer,
        )

        return PipelineResult(
            route="database",
            answer_markdown=final_answer,
            sources=final_retrieved_chunks,
            debug=debug,
        )

    def _chat_reply(self, query: str) -> str:
        if not self.groq_client.api_key:
            return "Hello! How can I help you with your PVD research today?"
        model = self.config.llm.chat_model or self.config.llm.router_model
        return self.groq_client.chat(
            model=model,
            system_prompt=CHAT_SYSTEM_PROMPT,
            user_prompt=query,
            temperature=0.4,
            max_tokens=256,
        ).strip()

    def _stage(self, name: str, action: Callable[[], T], fallback: T) -> T:
        try:
            return action()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Pipeline stage '%s' failed: %s", name, exc)
            return fallback

    @staticmethod
    def _fallback_grounded_answer(chunks: list[RetrievedChunk]) -> str:
        sections = [
            "I found relevant evidence in the indexed literature, but the answer synthesis stage is unavailable right now.",
            "Most relevant retrieved chunks:",
        ]
        for index, chunk in enumerate(chunks, start=1):
            snippet = chunk.text.strip()
            if len(snippet) > 320:
                snippet = snippet[:317].rstrip() + "..."
            sections.append(f"[Chunk {index}] {snippet}")
        return "\n\n".join(sections)
