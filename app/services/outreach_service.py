"""Build an OutreachMessage draft for recruiter review. Does not send email."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import ValidationError

from app.agents.outreach_agent import OutreachAgent
from app.candidates.availability_filter import evaluate_open_to_work
from app.config.settings import Settings, get_settings
from app.database.models.candidate import Candidate
from app.database.models.job import Job
from app.database.models.job_candidate import JobCandidate
from app.database.models.outreach import OutreachMessageRecord
from app.database.repositories.outreach_repository import OutreachRepository
from app.database.repositories.recruiter_repository import RecruiterRepository
from app.models.candidate import CandidateProfile
from app.models.job import JobProfile
from app.models.match import MatchResult
from app.models.outreach import OutreachTemplateType, RecruiterCompanyInfo
from app.schemas.outreach import OutreachDraftResponse
from app.services.recruiter_service import _signal_from_candidate
from app.workflow.audit import log_outreach_draft
from app.workflow.outreach_gate import OutreachHandoffDeniedError


class OutreachService:
    def __init__(
        self,
        outreach_repository: OutreachRepository,
        recruiter_repository: RecruiterRepository,
        *,
        agent: OutreachAgent | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.outreach_repository = outreach_repository
        self.recruiter_repository = recruiter_repository
        self.agent = agent or OutreachAgent()
        self.settings = settings or get_settings()

    async def generate_draft(
        self,
        job_id: uuid.UUID,
        candidate_id: uuid.UUID,
        *,
        recruiter_id: str,
        template: OutreachTemplateType | str = OutreachTemplateType.INITIAL,
        use_llm: bool = True,
    ) -> OutreachDraftResponse | None:
        loaded = await self._load(job_id, candidate_id)
        if loaded is None:
            return None
        job, candidate, match_row = loaded
        self._require_open_to_work(match_row, candidate)
        message = self.agent.generate(
            candidate_row_to_profile(candidate),
            job_row_to_profile(job),
            match_row_to_result(match_row),
            recruiter_info_from_settings(self.settings),
            template=template,
            use_llm=use_llm,
        )
        row = await self.outreach_repository.upsert_draft(
            message, recruiter_id=recruiter_id
        )
        log_outreach_draft(
            job_id=job_id,
            candidate_id=candidate_id,
            recruiter_id=recruiter_id,
            template=message.template.value,
        )
        return _to_response(row, generated=True)

    async def get_draft(
        self,
        job_id: uuid.UUID,
        candidate_id: uuid.UUID,
        *,
        template: OutreachTemplateType | str = OutreachTemplateType.INITIAL,
    ) -> OutreachDraftResponse | None:
        template_value = (
            template.value
            if isinstance(template, OutreachTemplateType)
            else OutreachTemplateType(template).value
        )
        row = await self.outreach_repository.get_draft(
            job_id, candidate_id, template_value
        )
        if row is None:
            return None
        return _to_response(row, generated=False)

    async def _load(
        self, job_id: uuid.UUID, candidate_id: uuid.UUID
    ) -> tuple[Job, Candidate, JobCandidate] | None:
        job = await self.recruiter_repository.get_job(job_id)
        candidate = await self.recruiter_repository.get_candidate(candidate_id)
        match_row = await self.recruiter_repository.get_job_candidate(
            job_id, candidate_id
        )
        if job is None or candidate is None or match_row is None:
            return None
        return job, candidate, match_row

    @staticmethod
    def _require_open_to_work(
        match_row: JobCandidate, candidate: Candidate
    ) -> None:
        del match_row
        eligibility = evaluate_open_to_work(
            candidate.id, _signal_from_candidate(candidate)
        )
        if not eligibility.eligible_for_outreach:
            raise OutreachHandoffDeniedError(
                "Candidate does not have an explicit eligible open-to-work "
                "status. No email will be sent."
            )


def candidate_row_to_profile(row: Candidate) -> CandidateProfile:
    return CandidateProfile(
        candidate_id=row.id,
        full_name=row.full_name,
        email=row.email,
        phone=row.phone,
        location=row.location,
        current_job_title=row.current_job_title,
        total_experience_years=row.total_experience_years,
        skills=list(row.skills or []),
        technical_skills=list(row.technical_skills or []),
        soft_skills=list(row.soft_skills or []),
        education=list(row.education or []),
        certifications=list(row.certifications or []),
        companies=list(row.companies or []),
        previous_roles=list(row.previous_roles or []),
        projects=list(row.projects or []),
        achievements=list(row.achievements or []),
        industries=list(row.industries or []),
        notice_period=row.notice_period,
        availability=row.availability,
        work_authorization=row.work_authorization,
        resume_summary=row.resume_summary,
    )


def job_row_to_profile(row: Job) -> JobProfile:
    payload = {
        "job_title": row.job_title,
        "experience_min": row.experience_min,
        "experience_max": row.experience_max,
        "location": row.location,
        "work_mode": row.work_mode,
        "employment_type": row.employment_type,
        "must_have_skills": list(row.must_have_skills or []),
        "preferred_skills": list(row.preferred_skills or []),
        "education": list(row.education or []),
        "responsibilities": list(row.responsibilities or []),
        "keywords": list(row.keywords or []),
    }
    try:
        return JobProfile.model_validate(payload)
    except ValidationError:
        payload["work_mode"] = None
        payload["employment_type"] = None
        return JobProfile.model_validate(payload)


def match_row_to_result(row: JobCandidate) -> MatchResult:
    generated = row.updated_at or row.created_at or datetime.now(UTC)
    if generated.tzinfo is None:
        generated = generated.replace(tzinfo=UTC)
    return MatchResult(
        candidate_id=row.candidate_id,
        job_id=row.job_id,
        overall_score=row.overall_score,
        required_skill_score=0,
        preferred_skill_score=0,
        experience_score=0,
        title_similarity_score=0,
        education_score=0,
        project_score=0,
        location_score=0,
        semantic_score=0,
        matched_requirements=list(row.matched_requirements or []),
        missing_requirements=list(row.missing_requirements or []),
        explanation=row.explanation or "",
        confidence=row.confidence or 0,
        generated_at=generated,
    )


def recruiter_info_from_settings(settings: Settings) -> RecruiterCompanyInfo:
    company = (settings.company_name or "").strip() or None
    name = (settings.recruiter_display_name or "").strip() or None
    title = (settings.recruiter_title or "").strip() or None
    email = (settings.recruiter_contact_email or "").strip() or None
    return RecruiterCompanyInfo(
        company_name=company,
        recruiter_name=name,
        recruiter_title=title,
        recruiter_email=email,
    )


def _to_response(
    row: OutreachMessageRecord, *, generated: bool
) -> OutreachDraftResponse:
    return OutreachDraftResponse(
        candidate_id=row.candidate_id,
        job_id=row.job_id,
        subject=row.subject,
        body=row.body,
        personalization_points=list(row.personalization_points or []),
        generated_at=row.generated_at,
        template=row.template,
        review_status=row.review_status,
        email_sent=bool(row.email_sent),
        recruiter_id=row.recruiter_id,
        message=(
            "Draft was already sent. Duplicate send is blocked."
            if row.email_sent
            else (
                "Draft saved for recruiter review. No email was sent."
                if generated
                else "Draft loaded for recruiter review. No email was sent."
            )
        ),
    )
