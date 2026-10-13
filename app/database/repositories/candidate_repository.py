"""Candidate repository. Isolated from the Resume Agent."""

from __future__ import annotations

import re
import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models.candidate import (
    CANDIDATE_STATUS_PARSED,
    Candidate,
    CandidateEvent,
    CandidateResume,
    CandidateSkill,
)
from app.models.candidate import CandidateProfile
from app.schemas.candidate import CandidateSearchQuery, ResumeFileRef
from app.utils.skills import canonicalize_skill


def normalize_email(email: str | None) -> str | None:
    if not email:
        return None
    return email.strip().lower() or None


def normalize_phone_digits(phone: str | None) -> str | None:
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    return digits or None


def _audit_payload(profile: CandidateProfile, *, file_path: str | None = None) -> dict:
    return {
        "has_name": profile.full_name is not None,
        "has_email": profile.email is not None,
        "has_phone": profile.phone is not None,
        "skill_count": len(profile.skills or []),
        "status": CANDIDATE_STATUS_PARSED,
        "file_path": file_path,
    }


def _skill_rows(candidate_id: uuid.UUID, profile: CandidateProfile) -> list[CandidateSkill]:
    rows: list[CandidateSkill] = []
    seen: set[tuple[str, str]] = set()
    groups = (
        ("technical", profile.technical_skills),
        ("soft", profile.soft_skills),
        ("general", profile.skills),
    )
    for kind, names in groups:
        for name in names:
            canonical = canonicalize_skill(name)
            if not canonical:
                continue
            key = (canonical.lower(), kind)
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                CandidateSkill(
                    candidate_id=candidate_id,
                    skill_name=name,
                    canonical_name=canonical,
                    skill_kind=kind,
                )
            )
    return rows


def _canonical_list(names: list[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for name in names:
        canonical = canonicalize_skill(name)
        if not canonical:
            continue
        key = canonical.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(canonical)
    return normalized


def _apply_profile(candidate: Candidate, profile: CandidateProfile) -> None:
    candidate.full_name = profile.full_name
    candidate.email = profile.email
    candidate.email_normalized = normalize_email(profile.email)
    candidate.phone = profile.phone
    candidate.phone_digits = normalize_phone_digits(profile.phone)
    candidate.location = profile.location
    candidate.current_job_title = profile.current_job_title
    candidate.total_experience_years = profile.total_experience_years
    candidate.notice_period = profile.notice_period
    candidate.availability = profile.availability
    candidate.work_authorization = profile.work_authorization
    candidate.resume_summary = profile.resume_summary
    candidate.education = [item.model_dump() for item in profile.education]
    candidate.certifications = [item.model_dump() for item in profile.certifications]
    candidate.companies = list(profile.companies)
    candidate.previous_roles = [item.model_dump() for item in profile.previous_roles]
    candidate.projects = [item.model_dump() for item in profile.projects]
    candidate.achievements = list(profile.achievements)
    candidate.industries = list(profile.industries)
    candidate.technical_skills = _canonical_list(profile.technical_skills)
    candidate.soft_skills = _canonical_list(profile.soft_skills)
    candidate.skills = _canonical_list(profile.skills)


def _resume_row(
    candidate_id: uuid.UUID, profile: CandidateProfile, file_ref: ResumeFileRef | None
) -> CandidateResume | None:
    path = file_ref.file_path if file_ref else None
    name = (file_ref.file_name if file_ref else None) or profile.resume_file_name
    source = (file_ref.source if file_ref else None) or profile.resume_source
    if not path and not name and not source:
        return None
    return CandidateResume(
        candidate_id=candidate_id,
        file_name=name,
        file_path=path,
        source=source,
        content_type=file_ref.content_type if file_ref else None,
        byte_size=file_ref.byte_size if file_ref else None,
        checksum_sha256=file_ref.checksum_sha256 if file_ref else None,
    )


class CandidateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        profile: CandidateProfile,
        file_ref: ResumeFileRef | None = None,
    ) -> Candidate:
        candidate = Candidate(id=uuid.uuid4(), status=CANDIDATE_STATUS_PARSED)
        _apply_profile(candidate, profile)
        self.session.add(candidate)
        await self.session.flush()

        candidate.skill_rows = _skill_rows(candidate.id, profile)
        resume = _resume_row(candidate.id, profile, file_ref)
        if resume is not None:
            candidate.resumes.append(resume)
        candidate.events.append(
            CandidateEvent(
                candidate_id=candidate.id,
                event_type="created",
                payload=_audit_payload(
                    profile, file_path=file_ref.file_path if file_ref else None
                ),
            )
        )
        await self.session.commit()
        await self.session.refresh(candidate)
        return candidate

    async def update(
        self,
        candidate_id: uuid.UUID,
        profile: CandidateProfile,
        file_ref: ResumeFileRef | None = None,
        *,
        status: str | None = None,
    ) -> Candidate | None:
        candidate = await self.get_by_id(candidate_id)
        if candidate is None:
            return None
        _apply_profile(candidate, profile)
        if status is not None:
            candidate.status = status
        candidate.skill_rows = _skill_rows(candidate.id, profile)
        resume = _resume_row(candidate.id, profile, file_ref)
        if resume is not None:
            candidate.resumes.append(resume)
        candidate.events.append(
            CandidateEvent(
                candidate_id=candidate.id,
                event_type="updated",
                payload=_audit_payload(
                    profile, file_path=file_ref.file_path if file_ref else None
                ),
            )
        )
        await self.session.commit()
        await self.session.refresh(candidate)
        return candidate

    async def get_by_id(self, candidate_id: uuid.UUID) -> Candidate | None:
        result = await self.session.execute(
            select(Candidate)
            .options(
                selectinload(Candidate.skill_rows),
                selectinload(Candidate.resumes),
                selectinload(Candidate.events),
            )
            .where(Candidate.id == candidate_id)
        )
        return result.scalar_one_or_none()

    async def find_duplicate(
        self, profile: CandidateProfile, *, exclude_id: uuid.UUID | None = None
    ) -> Candidate | None:
        email_key = normalize_email(profile.email)
        phone_key = normalize_phone_digits(profile.phone)
        if email_key is None and phone_key is None:
            return None
        stmt = select(Candidate)
        if email_key is not None and phone_key is not None:
            stmt = stmt.where(
                (Candidate.email_normalized == email_key)
                | (Candidate.phone_digits == phone_key)
            )
        elif email_key is not None:
            stmt = stmt.where(Candidate.email_normalized == email_key)
        else:
            stmt = stmt.where(Candidate.phone_digits == phone_key)
        if exclude_id is not None:
            stmt = stmt.where(Candidate.id != exclude_id)
        result = await self.session.execute(stmt.limit(1))
        return result.scalar_one_or_none()

    async def search(self, query: CandidateSearchQuery) -> list[Candidate]:
        stmt = select(Candidate)
        if query.skill:
            canonical = canonicalize_skill(query.skill).lower()
            stmt = (
                stmt.join(CandidateSkill)
                .where(CandidateSkill.canonical_name.ilike(canonical))
                .distinct()
            )
        if query.location:
            stmt = stmt.where(Candidate.location.ilike(f"%{query.location.strip()}%"))
        if query.job_title:
            stmt = stmt.where(
                Candidate.current_job_title.ilike(f"%{query.job_title.strip()}%")
            )
        if query.status:
            stmt = stmt.where(Candidate.status == query.status)
        if query.name:
            stmt = stmt.where(Candidate.full_name.ilike(f"%{query.name.strip()}%"))
        stmt = stmt.order_by(Candidate.updated_at.desc()).limit(query.limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search_for_sourcing(
        self,
        *,
        skills: list[str],
        job_title: str | None,
        location: str | None,
        limit: int = 100,
    ) -> list[Candidate]:
        """Return existing stored candidates only. Never creates rows."""
        filters = []
        canonical_skills = [
            canonicalize_skill(skill)
            for skill in skills
            if skill and canonicalize_skill(skill).strip()
        ]
        if canonical_skills:
            lowered = [name.lower() for name in canonical_skills]
            json_matches = [
                Candidate.id.in_(
                    select(CandidateSkill.candidate_id).where(
                        func.lower(CandidateSkill.canonical_name).in_(lowered)
                    )
                )
            ]
            for skill in canonical_skills:
                json_matches.append(Candidate.skills.contains([skill]))
                json_matches.append(Candidate.technical_skills.contains([skill]))
            filters.append(or_(*json_matches))
        title = (job_title or "").strip()
        if title:
            title_filters = [Candidate.current_job_title.ilike(f"%{title}%")]
            for token in title.replace("/", " ").replace("-", " ").split():
                if len(token) > 2:
                    title_filters.append(Candidate.current_job_title.ilike(f"%{token}%"))
            filters.append(or_(*title_filters))
        if not filters:
            return []
        del location  # location is scored later; do not drop stored candidates here
        stmt = select(Candidate).where(or_(*filters)).order_by(
            Candidate.updated_at.desc()
        ).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
