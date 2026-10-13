"""Recruiter review service. Does not send email or run matching."""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

from app.candidates.availability_filter import (
    OpenToWorkSignal,
    OpenToWorkStatus,
    evaluate_open_to_work,
)
from app.database.models.candidate import Candidate, CandidateResume
from app.database.models.job_candidate import (
    REVIEW_APPROVED,
    REVIEW_ON_HOLD,
    REVIEW_PENDING,
    REVIEW_REJECTED,
)
from app.database.repositories.recruiter_repository import (
    REVIEW_STATUSES,
    RecruiterRepository,
)
from app.models.ranking import RankedCandidate
from app.schemas.recruiter import (
    RecruiterCandidateProfile,
    RecruiterCandidateRow,
    RecruiterDashboard,
    RecruiterDecisionResponse,
    RecruiterJobSummary,
    ResumeAccess,
)
from app.workflow.states import WorkflowState

DECISION_MESSAGES = {
    REVIEW_APPROVED: "Candidate approved for recruiter review. No email was sent.",
    REVIEW_REJECTED: "Candidate rejected for recruiter review. No email was sent.",
    REVIEW_ON_HOLD: "Candidate put on hold for recruiter review. No email was sent.",
    REVIEW_PENDING: "Candidate returned to pending review. No email was sent.",
}

AVAILABILITY_FILTERS = {
    "open_to_work": "Open to Work",
    "not_open_to_work": "Not Open to Work",
    "unknown": "Unknown",
}


def _status_label(status: OpenToWorkStatus) -> str:
    if status is OpenToWorkStatus.OPEN_TO_WORK:
        return "Open to Work"
    if status is OpenToWorkStatus.NOT_OPEN_TO_WORK:
        return "Not Open to Work"
    return "Unknown"


def _signal_from_candidate(candidate: Candidate) -> OpenToWorkSignal | None:
    source = candidate.open_to_work_source
    if not source:
        return None
    raw = (candidate.open_to_work_status or "").strip() or OpenToWorkStatus.UNKNOWN
    try:
        status = OpenToWorkStatus(raw)
    except ValueError:
        return None
    return OpenToWorkSignal(
        status=status,
        source=source,
        verified_at=candidate.open_to_work_verified_at,
    )


def _opt_str(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _opt_float(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _json_list(value: object) -> list:
    return list(value) if isinstance(value, list) else []


def _has_resume(candidate: Candidate) -> bool:
    resumes = getattr(candidate, "resumes", None)
    return bool(resumes) if isinstance(resumes, list) else False


class RecruiterService:
    def __init__(self, repository: RecruiterRepository, workflow_service=None) -> None:
        self.repository = repository
        self.workflow_service = workflow_service

    async def get_dashboard(
        self,
        job_id: uuid.UUID,
        *,
        query: str | None = None,
        availability: str | None = None,
        review_status: str | None = None,
        sort: str = "match_score",
        sort_dir: str = "desc",
    ) -> RecruiterDashboard | None:
        job = await self.repository.get_job(job_id)
        if job is None:
            return None
        rows = await self.repository.list_job_candidates(job_id)
        display: list[RecruiterCandidateRow] = []
        open_to_work_count = 0
        pending_review_count = 0
        approved_count = 0
        rejected_count = 0
        on_hold_count = 0
        for row in rows:
            candidate = await self.repository.get_candidate(row.candidate_id)
            if candidate is None:
                continue
            eligibility = evaluate_open_to_work(
                candidate.id, _signal_from_candidate(candidate)
            )
            if eligibility.availability_status is OpenToWorkStatus.OPEN_TO_WORK:
                open_to_work_count += 1
            if row.review_status == REVIEW_PENDING:
                pending_review_count += 1
            elif row.review_status == REVIEW_APPROVED:
                approved_count += 1
            elif row.review_status == REVIEW_REJECTED:
                rejected_count += 1
            elif row.review_status == REVIEW_ON_HOLD:
                on_hold_count += 1
            display.append(
                RecruiterCandidateRow(
                    candidate_id=candidate.id,
                    name=_opt_str(candidate.full_name),
                    match_percent=int(round(row.overall_score * 100)),
                    availability_status=_status_label(eligibility.availability_status),
                    eligible_for_outreach=eligibility.eligible_for_outreach,
                    review_status=row.review_status,
                    workflow_status=getattr(
                        row, "workflow_status", WorkflowState.PENDING_REVIEW.value
                    )
                    if isinstance(getattr(row, "workflow_status", None), str)
                    else WorkflowState.PENDING_REVIEW.value,
                    explanation=row.explanation,
                    matched_requirements=list(row.matched_requirements or []),
                    missing_requirements=list(row.missing_requirements or []),
                    confidence=row.confidence,
                    current_job_title=_opt_str(candidate.current_job_title),
                    location=_opt_str(candidate.location),
                    has_resume=_has_resume(candidate),
                )
            )
        filtered = _filter_candidates(
            display,
            query=query,
            availability=availability,
            review_status=review_status,
        )
        filtered = _sort_candidates(filtered, sort=sort, sort_dir=sort_dir)
        return RecruiterDashboard(
            job_id=job.id,
            job_title=_opt_str(job.job_title),
            location=_opt_str(job.location),
            work_mode=_opt_str(job.work_mode),
            employment_type=_opt_str(job.employment_type),
            experience_min=_opt_float(job.experience_min),
            experience_max=_opt_float(job.experience_max),
            must_have_skills=_str_list(job.must_have_skills),
            preferred_skills=_str_list(job.preferred_skills),
            education=_str_list(job.education),
            responsibilities=_str_list(job.responsibilities),
            matched_count=len(rows),
            open_to_work_count=open_to_work_count,
            pending_review_count=pending_review_count,
            approved_count=approved_count,
            rejected_count=rejected_count,
            on_hold_count=on_hold_count,
            candidates=filtered,
        )

    async def list_job_summaries(self) -> list[RecruiterJobSummary]:
        jobs = await self.repository.list_jobs()
        summaries: list[RecruiterJobSummary] = []
        for job in jobs:
            dashboard = await self.get_dashboard(job.id)
            if dashboard is not None:
                summaries.append(
                    RecruiterJobSummary(
                        job_id=dashboard.job_id,
                        job_title=dashboard.job_title,
                        location=dashboard.location,
                        work_mode=dashboard.work_mode,
                        employment_type=dashboard.employment_type,
                        matched_count=dashboard.matched_count,
                        open_to_work_count=dashboard.open_to_work_count,
                        pending_review_count=dashboard.pending_review_count,
                        approved_count=dashboard.approved_count,
                        rejected_count=dashboard.rejected_count,
                        on_hold_count=dashboard.on_hold_count,
                    )
                )
        return summaries

    async def record_shortlist(
        self, job_id: uuid.UUID, ranked: list[RankedCandidate]
    ) -> RecruiterDashboard | None:
        job = await self.repository.get_job(job_id)
        if job is None:
            return None
        rows = await self.repository.upsert_shortlist(job_id, ranked)
        if self.workflow_service is not None:
            await self.workflow_service.record_shortlist_pipeline(rows)
        return await self.get_dashboard(job_id)

    async def decide(
        self,
        job_id: uuid.UUID,
        candidate_id: uuid.UUID,
        review_status: str,
        *,
        recruiter_id: str | None = None,
        reason: str | None = None,
    ) -> RecruiterDecisionResponse | None:
        if review_status not in REVIEW_STATUSES:
            raise ValueError("invalid review status")
        workflow_status = None
        if self.workflow_service is not None:
            history = await self.workflow_service.apply_review_action(
                job_id,
                candidate_id,
                review_status,
                recruiter_id=recruiter_id,
                reason=reason,
            )
            if history is None:
                return None
            workflow_status = history.workflow_status
            review_status = history.review_status
        else:
            row = await self.repository.set_review_status(
                job_id, candidate_id, review_status
            )
            if row is None:
                return None
        candidate = await self.repository.get_candidate(candidate_id)
        eligible = False
        if candidate is not None:
            eligible = evaluate_open_to_work(
                candidate.id, _signal_from_candidate(candidate)
            ).eligible_for_outreach
        return RecruiterDecisionResponse(
            job_id=job_id,
            candidate_id=candidate_id,
            review_status=review_status,
            workflow_status=workflow_status,
            eligible_for_outreach=eligible,
            communications_sent=False,
            message=DECISION_MESSAGES[review_status],
        )

    async def get_candidate_profile(
        self, job_id: uuid.UUID, candidate_id: uuid.UUID
    ) -> RecruiterCandidateProfile | None:
        job = await self.repository.get_job(job_id)
        match = await self.repository.get_job_candidate(job_id, candidate_id)
        candidate = await self.repository.get_candidate(candidate_id)
        if job is None or match is None or candidate is None:
            return None
        eligibility = evaluate_open_to_work(
            candidate.id, _signal_from_candidate(candidate)
        )
        resumes = [
            _resume_access(item, candidate.id)
            for item in (candidate.resumes or [])
            if isinstance(item, CandidateResume)
        ]
        return RecruiterCandidateProfile(
            job_id=job.id,
            job_title=_opt_str(job.job_title),
            candidate_id=candidate.id,
            name=_opt_str(candidate.full_name),
            email=_opt_str(candidate.email),
            phone=_opt_str(candidate.phone),
            location=_opt_str(candidate.location),
            current_job_title=_opt_str(candidate.current_job_title),
            total_experience_years=_opt_float(candidate.total_experience_years),
            technical_skills=_str_list(candidate.technical_skills),
            skills=_str_list(candidate.skills),
            soft_skills=_str_list(candidate.soft_skills),
            education=_json_list(candidate.education),
            certifications=_json_list(candidate.certifications),
            previous_roles=_json_list(candidate.previous_roles),
            projects=_json_list(candidate.projects),
            companies=_str_list(candidate.companies),
            achievements=_str_list(candidate.achievements),
            industries=_str_list(candidate.industries),
            resume_summary=_opt_str(candidate.resume_summary),
            resumes=resumes,
            availability_status=_status_label(eligibility.availability_status),
            open_to_work_source=_opt_str(candidate.open_to_work_source),
            open_to_work_verified_at=(
                candidate.open_to_work_verified_at
                if isinstance(candidate.open_to_work_verified_at, datetime)
                else None
            ),
            eligible_for_outreach=eligibility.eligible_for_outreach,
            match_percent=int(round(match.overall_score * 100)),
            matched_requirements=list(match.matched_requirements or []),
            missing_requirements=list(match.missing_requirements or []),
            explanation=match.explanation,
            confidence=match.confidence,
            review_status=match.review_status,
            workflow_status=getattr(match, "workflow_status", None)
            if isinstance(getattr(match, "workflow_status", None), str)
            else WorkflowState.PENDING_REVIEW.value,
            communications_sent=False,
        )

    async def get_resume_file(
        self, candidate_id: uuid.UUID, resume_id: uuid.UUID
    ) -> tuple[Path, str | None] | None:
        resume = await self.repository.get_resume(candidate_id, resume_id)
        if resume is None or not resume.file_path:
            return None
        path = Path(resume.file_path)
        if not path.is_file():
            return None
        return path, resume.file_name


def _filter_candidates(
    rows: list[RecruiterCandidateRow],
    *,
    query: str | None,
    availability: str | None,
    review_status: str | None,
) -> list[RecruiterCandidateRow]:
    filtered = rows
    needle = (query or "").strip().lower()
    if needle:
        filtered = [
            row
            for row in filtered
            if needle in (row.name or "").lower()
            or needle in (row.current_job_title or "").lower()
            or needle in (row.location or "").lower()
            or any(needle in item.lower() for item in row.matched_requirements)
            or any(needle in item.lower() for item in row.missing_requirements)
        ]
    availability_key = (availability or "all").strip().lower()
    if availability_key in AVAILABILITY_FILTERS:
        label = AVAILABILITY_FILTERS[availability_key]
        filtered = [row for row in filtered if row.availability_status == label]
    status_key = (review_status or "all").strip().lower()
    if status_key in REVIEW_STATUSES:
        filtered = [row for row in filtered if row.review_status == status_key]
    return filtered


def _sort_candidates(
    rows: list[RecruiterCandidateRow], *, sort: str, sort_dir: str
) -> list[RecruiterCandidateRow]:
    descending = (sort_dir or "desc").strip().lower() != "asc"
    key = (sort or "match_score").strip().lower()
    if key == "name":
        return sorted(
            rows, key=lambda item: (item.name or "").lower(), reverse=descending
        )
    if key == "status":
        return sorted(rows, key=lambda item: item.review_status, reverse=descending)
    if descending:
        return sorted(rows, key=lambda item: (-item.match_percent, item.name or ""))
    return sorted(rows, key=lambda item: (item.match_percent, item.name or ""))


def _resume_access(resume: CandidateResume, candidate_id: uuid.UUID) -> ResumeAccess:
    path = Path(resume.file_path) if resume.file_path else None
    available = bool(path and path.is_file())
    download_path = (
        f"/api/v1/recruiter/candidates/{candidate_id}/resumes/{resume.id}/file"
        if available
        else None
    )
    return ResumeAccess(
        resume_id=resume.id,
        file_name=resume.file_name,
        source=resume.source,
        content_type=resume.content_type,
        byte_size=resume.byte_size,
        available_on_server=available,
        download_path=download_path,
    )
