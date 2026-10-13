"""Run sourcing → match → rank → recruiter shortlist. Never hires or emails."""

from __future__ import annotations

import uuid
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.matching_agent import MatchingAgent
from app.agents.sourcing_agent import SourcingAgent
from app.database.repositories.candidate_repository import CandidateRepository
from app.database.repositories.recruiter_repository import RecruiterRepository
from app.matching.ranking_engine import RankingEngine
from app.models.ranking import RankedCandidate
from app.models.sourcing import SourcedCandidateRef
from app.services.outreach_service import candidate_row_to_profile, job_row_to_profile
from app.services.recruiter_service import RecruiterService
from app.services.sourcing_service import SourcingService


class PipelineState(TypedDict, total=False):
    job_id: str
    sourced_count: int
    matched_count: int
    ranked_count: int
    shortlist_recorded: bool
    outreach_sent: bool
    hired: bool
    errors: list[str]
    sourced: list[dict]
    ranked: list[dict]


class RecruitmentPipeline:
    """LangGraph orchestration of completed agents. Stops at recruiter review."""

    def __init__(
        self,
        sourcing_service: SourcingService,
        recruiter_service: RecruiterService,
        candidate_repository: CandidateRepository,
        recruiter_repository: RecruiterRepository,
        *,
        matching_agent: MatchingAgent | None = None,
        ranking_engine: RankingEngine | None = None,
    ) -> None:
        self.sourcing_service = sourcing_service
        self.recruiter_service = recruiter_service
        self.candidate_repository = candidate_repository
        self.recruiter_repository = recruiter_repository
        self.matching_agent = matching_agent or MatchingAgent()
        self.ranking_engine = ranking_engine or RankingEngine()

    def compile(self):
        graph = StateGraph(PipelineState)
        graph.add_node("source", self._source)
        graph.add_node("match_and_rank", self._match_and_rank)
        graph.add_node("record_shortlist", self._record_shortlist)
        graph.add_node("human_gate", self._human_gate)
        graph.add_edge(START, "source")
        graph.add_edge("source", "match_and_rank")
        graph.add_edge("match_and_rank", "record_shortlist")
        graph.add_edge("record_shortlist", "human_gate")
        graph.add_edge("human_gate", END)
        return graph.compile()

    async def run(self, job_id: uuid.UUID) -> PipelineState:
        graph = self.compile()
        return await graph.ainvoke(
            {
                "job_id": str(job_id),
                "outreach_sent": False,
                "hired": False,
                "errors": [],
            }
        )

    async def _source(self, state: PipelineState) -> dict[str, Any]:
        job_id = uuid.UUID(state["job_id"])
        result = await self.sourcing_service.source_job(job_id)
        if result is None:
            return {
                "errors": [*(state.get("errors") or []), "Job not found"],
                "sourced_count": 0,
                "sourced": [],
            }
        return {
            "sourced_count": len(result.candidates),
            "sourced": [item.model_dump(mode="json") for item in result.candidates],
        }

    async def _match_and_rank(self, state: PipelineState) -> dict[str, Any]:
        if state.get("errors"):
            return {"matched_count": 0, "ranked_count": 0, "ranked": []}
        job_id = uuid.UUID(state["job_id"])
        job = await self.recruiter_repository.get_job(job_id)
        if job is None:
            return {
                "errors": [*(state.get("errors") or []), "Job not found"],
                "matched_count": 0,
                "ranked_count": 0,
                "ranked": [],
            }
        job_profile = job_row_to_profile(job)
        matches = []
        for raw in state.get("sourced") or []:
            ref = SourcedCandidateRef.model_validate(raw)
            row = await self.candidate_repository.get_by_id(ref.candidate_id)
            if row is None:
                continue
            candidate = candidate_row_to_profile(row)
            matches.append(
                self.matching_agent.match(
                    candidate,
                    job_profile,
                    job_id=job_id,
                    candidate_id=row.id,
                )
            )
        ranked = self.ranking_engine.generate_shortlist(job_id, matches)
        return {
            "matched_count": len(matches),
            "ranked_count": len(ranked),
            "ranked": [item.model_dump(mode="json") for item in ranked],
        }

    async def _record_shortlist(self, state: PipelineState) -> dict[str, Any]:
        if state.get("errors") or not state.get("ranked"):
            return {"shortlist_recorded": False}
        job_id = uuid.UUID(state["job_id"])
        ranked = [RankedCandidate.model_validate(item) for item in state["ranked"]]
        dashboard = await self.recruiter_service.record_shortlist(job_id, ranked)
        return {"shortlist_recorded": dashboard is not None}

    async def _human_gate(self, state: PipelineState) -> dict[str, Any]:
        del state
        return {
            "outreach_sent": False,
            "hired": False,
        }


def build_default_pipeline(
    session,
) -> RecruitmentPipeline:
    recruiter_repository = RecruiterRepository(session)
    candidate_repository = CandidateRepository(session)
    from app.database.repositories.workflow_repository import WorkflowRepository
    from app.services.workflow_service import WorkflowService

    recruiter_service = RecruiterService(
        recruiter_repository,
        WorkflowService(WorkflowRepository(session), recruiter_repository),
    )
    sourcing = SourcingService(
        candidate_repository, recruiter_repository, agent=SourcingAgent()
    )
    return RecruitmentPipeline(
        sourcing, recruiter_service, candidate_repository, recruiter_repository
    )
