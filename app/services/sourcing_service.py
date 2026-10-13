"""Source existing ATS candidates for a job. Does not invent people or email them."""

from __future__ import annotations

import uuid

from app.agents.sourcing_agent import SourcingAgent
from app.database.repositories.candidate_repository import CandidateRepository
from app.database.repositories.recruiter_repository import RecruiterRepository
from app.models.sourcing import SourcingQuery, SourcingResult
from app.services.outreach_service import candidate_row_to_profile, job_row_to_profile


class SourcingServiceError(Exception):
    """Sourcing orchestration error."""


class SourcingService:
    def __init__(
        self,
        candidate_repository: CandidateRepository,
        recruiter_repository: RecruiterRepository,
        *,
        agent: SourcingAgent | None = None,
    ) -> None:
        self.candidate_repository = candidate_repository
        self.recruiter_repository = recruiter_repository
        self.agent = agent or SourcingAgent()

    async def source_job(self, job_id: uuid.UUID) -> SourcingResult | None:
        job = await self.recruiter_repository.get_job(job_id)
        if job is None:
            return None
        profile = job_row_to_profile(job)
        queries = self.agent.plan(profile)
        stored = await self._load_existing(queries)
        mapped = [candidate_row_to_profile(row) for row in stored]
        return self.agent.select(profile, mapped, source="internal_ats")

    async def _load_existing(self, queries: list[SourcingQuery]):
        seen: dict = {}
        for query in queries:
            rows = await self.candidate_repository.search_for_sourcing(
                skills=query.skills,
                job_title=query.job_title,
                location=query.location,
            )
            for row in rows:
                seen[row.id] = row
        return list(seen.values())
