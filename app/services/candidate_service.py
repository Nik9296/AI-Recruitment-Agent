"""Persistence service for Resume Agent CandidateProfile records."""

from __future__ import annotations

import uuid

from app.database.models.candidate import Candidate
from app.database.repositories.candidate_repository import CandidateRepository
from app.models.candidate import CandidateProfile
from app.schemas.candidate import CandidateSearchQuery, ResumeFileRef


class DuplicateCandidateError(Exception):
    """Raised when email or phone already belongs to another candidate."""


class CandidateService:
    def __init__(self, repository: CandidateRepository) -> None:
        self.repository = repository

    async def create_candidate(
        self,
        profile: CandidateProfile,
        file_ref: ResumeFileRef | None = None,
    ) -> Candidate:
        duplicate = await self.repository.find_duplicate(profile)
        if duplicate is not None:
            raise DuplicateCandidateError(
                "A candidate with this email or phone already exists"
            )
        return await self.repository.create(profile, file_ref)

    async def update_candidate(
        self,
        candidate_id: uuid.UUID,
        profile: CandidateProfile,
        file_ref: ResumeFileRef | None = None,
        *,
        status: str | None = None,
    ) -> Candidate | None:
        duplicate = await self.repository.find_duplicate(
            profile, exclude_id=candidate_id
        )
        if duplicate is not None:
            raise DuplicateCandidateError(
                "A candidate with this email or phone already exists"
            )
        return await self.repository.update(
            candidate_id, profile, file_ref, status=status
        )

    async def get_candidate(self, candidate_id: uuid.UUID) -> Candidate | None:
        return await self.repository.get_by_id(candidate_id)

    async def search_candidates(
        self, query: CandidateSearchQuery | None = None
    ) -> list[Candidate]:
        return await self.repository.search(query or CandidateSearchQuery())
