from __future__ import annotations

from dataclasses import asdict

from pld_copilot.agents.critic import CriticAgent
from pld_copilot.agents.director import DirectorAgent
from pld_copilot.agents.formatter import FormatterAgent
from pld_copilot.agents.grader import DocumentGraderAgent
from pld_copilot.agents.investigator import PrincipalInvestigatorAgent
from pld_copilot.agents.retriever import DataEngineerAgent
from pld_copilot.agents.rewriter import QueryRewriterAgent
from pld_copilot.config import AppConfig
from pld_copilot.llm import LocalOpenAICompatibleClient
from pld_copilot.models import PipelineResult, RetrievedChunk


class PLDCopilotPipeline:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.client = LocalOpenAICompatibleClient(
            base_url=config.llm.base_url,
            api_key=config.llm.api_key,
            temperature=config.llm.temperature,
            timeout_seconds=config.llm.timeout_seconds,
        )
        self.director = DirectorAgent(self.client, config)
        self.rewriter = QueryRewriterAgent(self.client, config)
        self.retriever = DataEngineerAgent(config)
        self.grader = DocumentGraderAgent(self.client, config)
        self.investigator = PrincipalInvestigatorAgent(self.client, config)
        self.critic = CriticAgent(self.client, config)
        self.formatter = FormatterAgent(self.client, config)

    @classmethod
    def from_config(cls, config: AppConfig) -> "PLDCopilotPipeline":
        return cls(config)

    def run(self, query: str) -> PipelineResult:
        route_decision = self.director.route(query)

        if route_decision.route == "chat":
            return PipelineResult(
                route="chat",
                answer_markdown=(
                    "This copilot is configured for local scientific assistance.\n\n"
                    "Your message looks conversational, so I did not query the literature database. "
                    "Ask a materials, PLD, thin-film, or experiment question to trigger evidence retrieval."
                ),
                citations=[],
                debug={"director_reason": route_decision.reason},
            )

        rewritten_query = self.rewriter.rewrite(query)

        if not self.retriever.available:
            return self._database_free_result(
                query=query,
                rewritten_query=rewritten_query,
                route_reason=route_decision.reason,
                metadata_filters=route_decision.metadata_filters,
            )

        approved_chunks = self._retrieve_until_approved(
            query=query,
            rewritten_query=rewritten_query,
            metadata_filters=route_decision.metadata_filters,
        )

        if not approved_chunks:
            return PipelineResult(
                route="database",
                answer_markdown=(
                    "I could not find enough relevant local evidence in the indexed corpus to answer this safely."
                ),
                citations=[],
                debug={
                    "director_reason": route_decision.reason,
                    "rewritten_query": rewritten_query,
                    "retriever_status": self.retriever.status(),
                },
            )

        draft = self.investigator.synthesize(query, approved_chunks)
        critic_result = self.critic.review(query=query, draft_answer=draft, evidence=approved_chunks)

        if not critic_result["pass"]:
            draft = self.investigator.synthesize(
                query=(
                    f"{query}\n\n"
                    "Revise the answer conservatively. Remove unsupported claims and stick tightly to the evidence."
                ),
                evidence=approved_chunks,
            )
            critic_result = self.critic.review(query=query, draft_answer=draft, evidence=approved_chunks)

        citations = sorted({chunk.doi for chunk in approved_chunks if chunk.doi})
        approved_answer = critic_result.get("approved_answer", draft)
        final_markdown = self.formatter.format(approved_answer)

        return PipelineResult(
            route="database",
            answer_markdown=final_markdown,
            citations=citations,
            debug={
                "director_reason": route_decision.reason,
                "metadata_filters": route_decision.metadata_filters,
                "rewritten_query": rewritten_query,
                "approved_chunk_count": len(approved_chunks),
                "approved_chunks": [asdict(chunk) for chunk in approved_chunks],
                "critic_issues": critic_result.get("issues", []),
                "retriever_status": self.retriever.status(),
            },
        )

    def _database_free_result(
        self,
        query: str,
        rewritten_query: str,
        route_reason: str,
        metadata_filters: dict,
    ) -> PipelineResult:
        answer_markdown = self.formatter.format(
            "\n".join(
                [
                    "## Database Not Connected",
                    "This query was routed to the scientific lane, but retrieval is currently disabled or ChromaDB is not installed.",
                    "",
                    f"**Original query:** {query}",
                    f"**Rewritten retrieval query:** {rewritten_query}",
                    "",
                    "### What still works right now",
                    "- Director routing",
                    "- Query rewriting",
                    "- Grok-based lane selection if configured",
                    "- Pipeline wiring for retriever, grader, PI, critic, and formatter",
                    "",
                    "### What is waiting on the database",
                    "- Evidence retrieval",
                    "- Relevance grading over retrieved chunks",
                    "- DOI-grounded scientific synthesis",
                    "",
                    "### Suggested next step",
                    "Set `retrieval.enabled: true` after your ChromaDB collection is ready, then run the ingest command.",
                ]
            )
        )
        return PipelineResult(
            route="database",
            answer_markdown=answer_markdown,
            citations=[],
            debug={
                "director_reason": route_reason,
                "metadata_filters": metadata_filters,
                "rewritten_query": rewritten_query,
                "retriever_status": self.retriever.status(),
            },
        )

    def _retrieve_until_approved(
        self,
        query: str,
        rewritten_query: str,
        metadata_filters: dict,
    ) -> list[RetrievedChunk]:
        for retry_round in range(self.config.policy.max_retry_rounds + 1):
            top_k = (
                self.config.retrieval.top_k
                if retry_round == 0
                else self.config.retrieval.retry_top_k
            )
            filters = metadata_filters if retry_round == 0 else {}
            chunks = self.retriever.retrieve(
                rewritten_query=rewritten_query,
                metadata_filters=filters,
                top_k=top_k,
            )
            graded = self.grader.grade(query=query, chunks=chunks)
            approved = [item.chunk for item in graded if item.relevant]

            if len(approved) >= self.config.retrieval.min_relevance_passes:
                return approved

        return []
