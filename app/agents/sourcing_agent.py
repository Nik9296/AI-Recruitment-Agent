"""Sourcing Agent: build search queries and filter real candidates.

Does not invent people, scrape the web, or persist records.
"""

from __future__ import annotations

import logging

from app.models.candidate import CandidateProfile
from app.models.job import JobProfile
from app.models.sourcing import SourcedCandidateRef, SourcingQuery, SourcingResult
from app.utils.matching import candidate_skill_pool, skill_covers, score_title
from app.utils.skills import canonicalize_skill

logger = logging.getLogger(__name__)


class SourcingAgentError(Exception):
    """Base sourcing error."""


class ExternalSourcingNotImplementedError(SourcingAgentError):
    """Reserved LinkedIn/job-board adapters are not wired."""


class SourcingAgent:
    """Turn a JobProfile into queries and keep only grounded candidate hits."""

    def plan(self, job: JobProfile) -> list[SourcingQuery]:
        skills = [canonicalize_skill(item) for item in job.must_have_skills if item]
        preferred = [canonicalize_skill(item) for item in job.preferred_skills if item]
        queries: list[SourcingQuery] = []
        if job.job_title or skills or job.location:
            queries.append(
                SourcingQuery(
                    job_title=job.job_title,
                    skills=skills[:12],
                    location=job.location,
                    experience_min=job.experience_min,
                    label="must_have",
                )
            )
        if preferred:
            queries.append(
                SourcingQuery(
                    job_title=job.job_title,
                    skills=preferred[:8],
                    location=job.location,
                    experience_min=job.experience_min,
                    label="preferred",
                )
            )
        return queries

    def select(
        self,
        job: JobProfile,
        profiles: list[CandidateProfile],
        *,
        source: str = "internal_ats",
    ) -> SourcingResult:
        queries = self.plan(job)
        wanted = [skill for query in queries for skill in query.skills]
        selected: list[SourcedCandidateRef] = []
        seen: set = set()
        for profile in profiles:
            if profile.candidate_id is None:
                continue
            if profile.candidate_id in seen:
                continue
            ref = self._match_ref(job, profile, wanted, source=source)
            if ref is None:
                continue
            seen.add(profile.candidate_id)
            selected.append(ref)
        logger.info(
            "SourcingAgent.select completed",
            extra={
                "query_count": len(queries),
                "input_profile_count": len(profiles),
                "selected_count": len(selected),
                "invented_candidates": False,
            },
        )
        return SourcingResult(
            job_title=job.job_title,
            queries=queries,
            candidates=selected,
            invented_candidates=False,
            external_providers_used=[],
        )

    def search_external(self, job: JobProfile) -> SourcingResult:
        del job
        raise ExternalSourcingNotImplementedError(
            "External sourcing (LinkedIn/job boards) is not wired. "
            "Use the internal ATS candidate store. No profiles were invented."
        )

    def _match_ref(
        self,
        job: JobProfile,
        profile: CandidateProfile,
        wanted_skills: list[str],
        *,
        source: str,
    ) -> SourcedCandidateRef | None:
        pool = candidate_skill_pool(profile)
        matched_skills = [
            canonicalize_skill(skill)
            for skill in wanted_skills
            if skill_covers(skill, pool)
        ]
        title_matched = score_title(job, profile) >= 0.45 if job.job_title else False
        if not matched_skills and not title_matched:
            return None
        return SourcedCandidateRef(
            candidate_id=profile.candidate_id,
            source=source,
            matched_query_skills=matched_skills[:12],
            title_matched=title_matched,
        )
