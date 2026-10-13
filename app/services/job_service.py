"""Persistence service for analyzed job profiles."""

from __future__ import annotations

import uuid

from app.database.models.job import Job
from app.database.repositories.job_repository import JobRepository
from app.models.job import JobProfile


class JobService:
    def __init__(self, repository: JobRepository) -> None:
        self.repository = repository

    async def save_analyzed_job(
        self, profile: JobProfile, raw_job_description: str
    ) -> Job:
        return await self.repository.save(profile, raw_job_description)

    async def get_job(self, job_id: uuid.UUID) -> Job | None:
        return await self.repository.get_by_id(job_id)
