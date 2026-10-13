"""Job repository. Isolated from the JD Agent."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.job import Job
from app.models.job import JobProfile


class JobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, profile: JobProfile, raw_job_description: str) -> Job:
        job = Job(
            job_title=profile.job_title,
            experience_min=profile.experience_min,
            experience_max=profile.experience_max,
            location=profile.location,
            work_mode=profile.work_mode.value if profile.work_mode else None,
            employment_type=(
                profile.employment_type.value if profile.employment_type else None
            ),
            must_have_skills=list(profile.must_have_skills),
            preferred_skills=list(profile.preferred_skills),
            education=list(profile.education),
            responsibilities=list(profile.responsibilities),
            keywords=list(profile.keywords),
            raw_job_description=raw_job_description,
        )
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def get_by_id(self, job_id: uuid.UUID) -> Job | None:
        result = await self.session.execute(select(Job).where(Job.id == job_id))
        return result.scalar_one_or_none()
