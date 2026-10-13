"""Recruiter dashboard persistence. Isolated from matching and outreach agents."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models.candidate import Candidate, CandidateResume
from app.database.models.job import Job
from app.database.models.job_candidate import (
    REVIEW_APPROVED,
    REVIEW_ON_HOLD,
    REVIEW_PENDING,
    REVIEW_REJECTED,
    JobCandidate,
)
from app.models.ranking import RankedCandidate

REVIEW_STATUSES = {
    REVIEW_PENDING,
    REVIEW_APPROVED,
    REVIEW_REJECTED,
    REVIEW_ON_HOLD,
}


class RecruiterRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_job(self, job_id: uuid.UUID) -> Job | None:
        result = await self.session.execute(select(Job).where(Job.id == job_id))
        return result.scalar_one_or_none()

    async def list_jobs(self) -> list[Job]:
        result = await self.session.execute(select(Job).order_by(Job.updated_at.desc()))
        return list(result.scalars().all())

    async def get_candidate(self, candidate_id: uuid.UUID) -> Candidate | None:
        result = await self.session.execute(
            select(Candidate)
            .options(selectinload(Candidate.resumes))
            .where(Candidate.id == candidate_id)
        )
        return result.scalar_one_or_none()

    async def list_job_candidates(self, job_id: uuid.UUID) -> list[JobCandidate]:
        result = await self.session.execute(
            select(JobCandidate)
            .where(JobCandidate.job_id == job_id)
            .order_by(JobCandidate.overall_score.desc())
        )
        return list(result.scalars().all())

    async def get_job_candidate(
        self, job_id: uuid.UUID, candidate_id: uuid.UUID
    ) -> JobCandidate | None:
        result = await self.session.execute(
            select(JobCandidate).where(
                JobCandidate.job_id == job_id,
                JobCandidate.candidate_id == candidate_id,
            )
        )
        return result.scalar_one_or_none()

    async def upsert_shortlist(
        self, job_id: uuid.UUID, ranked: list[RankedCandidate]
    ) -> list[JobCandidate]:
        rows: list[JobCandidate] = []
        for item in ranked:
            if item.candidate_id is None:
                continue
            existing = await self.get_job_candidate(job_id, item.candidate_id)
            if existing is None:
                existing = JobCandidate(
                    job_id=job_id,
                    candidate_id=item.candidate_id,
                    review_status=REVIEW_PENDING,
                )
                self.session.add(existing)
            existing.overall_score = item.overall_score
            existing.matched_requirements = list(item.matched_requirements)
            existing.missing_requirements = list(item.missing_requirements)
            existing.explanation = item.explanation
            existing.confidence = item.confidence
            rows.append(existing)
        await self.session.commit()
        for row in rows:
            await self.session.refresh(row)
        return rows

    async def get_resume(
        self, candidate_id: uuid.UUID, resume_id: uuid.UUID
    ) -> CandidateResume | None:
        result = await self.session.execute(
            select(CandidateResume).where(
                CandidateResume.id == resume_id,
                CandidateResume.candidate_id == candidate_id,
            )
        )
        return result.scalar_one_or_none()

    async def set_review_status(
        self, job_id: uuid.UUID, candidate_id: uuid.UUID, review_status: str
    ) -> JobCandidate | None:
        if review_status not in REVIEW_STATUSES:
            raise ValueError("invalid review status")
        row = await self.get_job_candidate(job_id, candidate_id)
        if row is None:
            return None
        row.review_status = review_status
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def set_open_to_work(
        self,
        candidate_id: uuid.UUID,
        status: str,
        source: str | None,
        verified_at,
    ) -> Candidate | None:
        candidate = await self.get_candidate(candidate_id)
        if candidate is None:
            return None
        candidate.open_to_work_status = status
        candidate.open_to_work_source = source
        candidate.open_to_work_verified_at = verified_at
        await self.session.commit()
        await self.session.refresh(candidate)
        return candidate
