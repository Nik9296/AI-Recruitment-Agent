"""Public candidate application service for recruiter jobs."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.availability_filter import OpenToWorkStatus
from app.database.models.candidate import CANDIDATE_STATUS_PARSED, Candidate
from app.database.models.job_candidate import REVIEW_PENDING, JobCandidate
from app.database.repositories.recruiter_repository import RecruiterRepository
from app.schemas.application import JobApplicationRequest, JobApplicationResponse
from app.workflow.states import WorkflowState


def _normalize_email(value: str | None) -> str | None:
    if not value:
        return None
    return value.strip().lower() or None


def _normalize_phone_digits(value: str | None) -> str | None:
    if not value:
        return None
    digits = re.sub(r"\D", "", value)
    return digits or None


class JobApplicationService:
    def __init__(self, session: AsyncSession, recruiter_repository: RecruiterRepository):
        self.session = session
        self.recruiter_repository = recruiter_repository

    async def apply(
        self, job_id: uuid.UUID, payload: JobApplicationRequest
    ) -> JobApplicationResponse | None:
        job = await self.recruiter_repository.get_job(job_id)
        if job is None:
            return None
        candidate, created_candidate = await self._upsert_candidate(payload)
        match = await self.recruiter_repository.get_job_candidate(job_id, candidate.id)
        created_match = False
        if match is None:
            self.session.add(
                JobCandidate(
                    job_id=job_id,
                    candidate_id=candidate.id,
                    overall_score=0.0,
                    matched_requirements=[],
                    missing_requirements=[],
                    explanation=(
                        "Candidate applied directly through the job application form. "
                        "Awaiting recruiter review and matching pipeline refresh."
                    ),
                    confidence=0.0,
                    review_status=REVIEW_PENDING,
                    workflow_status=WorkflowState.PENDING_REVIEW.value,
                )
            )
            created_match = True
        await self.session.commit()
        return JobApplicationResponse(
            job_id=job_id,
            candidate_id=candidate.id,
            created_candidate=created_candidate,
            created_match=created_match,
            applied_at=datetime.now(UTC),
            message=(
                "Application submitted successfully. Recruiter will review your profile."
            ),
        )

    async def _upsert_candidate(
        self, payload: JobApplicationRequest
    ) -> tuple[Candidate, bool]:
        email_key = _normalize_email(payload.email)
        phone_key = _normalize_phone_digits(payload.phone)
        candidate = None
        if email_key or phone_key:
            filters = []
            if email_key:
                filters.append(Candidate.email_normalized == email_key)
            if phone_key:
                filters.append(Candidate.phone_digits == phone_key)
            result = await self.session.execute(
                select(Candidate).where(or_(*filters)).limit(1)
            )
            candidate = result.scalar_one_or_none()
        created = candidate is None
        if candidate is None:
            candidate = Candidate(id=uuid.uuid4(), status=CANDIDATE_STATUS_PARSED)
            self.session.add(candidate)
        candidate.full_name = payload.full_name
        candidate.email = payload.email
        candidate.email_normalized = email_key
        candidate.phone = payload.phone
        candidate.phone_digits = phone_key
        candidate.location = payload.location
        candidate.current_job_title = payload.current_job_title
        candidate.resume_summary = payload.resume_summary
        candidate.skills = list(payload.skills or [])
        candidate.technical_skills = list(payload.skills or [])
        candidate.open_to_work_status = (
            OpenToWorkStatus.OPEN_TO_WORK.value
            if payload.open_to_work
            else OpenToWorkStatus.NOT_OPEN_TO_WORK.value
        )
        candidate.open_to_work_source = "candidate_declaration"
        candidate.open_to_work_verified_at = datetime.now(UTC)
        await self.session.flush()
        return candidate, created
