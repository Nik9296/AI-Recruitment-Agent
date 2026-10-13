"""Open-to-work eligibility for automated outreach.

Never infers status from resumes, job changes, gaps, or profile activity.
Does not delete candidates; ineligible people stay in storage and are only
excluded from automated outreach.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel

PERMITTED_SOURCES = frozenset(
    {
        "candidate_declaration",
        "recruiter_recorded",
        "ats_open_to_work",
        "linkedin_open_to_work",
    }
)

FORBIDDEN_INFERENCE_SOURCES = frozenset(
    {
        "resume",
        "resume_availability",
        "notice_period",
        "job_change",
        "employment_gap",
        "profile_activity",
        "inferred",
        "guess",
        "llm",
        "matching_agent",
    }
)


class OpenToWorkStatus(StrEnum):
    OPEN_TO_WORK = "OPEN_TO_WORK"
    NOT_OPEN_TO_WORK = "NOT_OPEN_TO_WORK"
    UNKNOWN = "UNKNOWN"


class OpenToWorkSignal(BaseModel):
    """Explicit open-to-work declaration. Not resume-derived availability."""

    status: OpenToWorkStatus
    source: str | None = None
    verified_at: datetime | None = None


class OutreachEligibility(BaseModel):
    candidate_id: UUID
    availability_status: OpenToWorkStatus
    eligible_for_outreach: bool
    source: str | None = None
    verified_at: datetime | None = None
    reason: str


def evaluate_open_to_work(
    candidate_id: UUID,
    signal: OpenToWorkSignal | None,
) -> OutreachEligibility:
    """Return outreach eligibility from an explicit signal only."""
    if signal is None:
        return OutreachEligibility(
            candidate_id=candidate_id,
            availability_status=OpenToWorkStatus.UNKNOWN,
            eligible_for_outreach=False,
            source=None,
            verified_at=None,
            reason=(
                "No explicit open-to-work signal. UNKNOWN: do not automatically "
                "contact. Candidate is retained."
            ),
        )

    source = (signal.source or "").strip() or None
    source_key = source.lower() if source else ""
    if source_key in FORBIDDEN_INFERENCE_SOURCES or not source_key:
        return OutreachEligibility(
            candidate_id=candidate_id,
            availability_status=OpenToWorkStatus.UNKNOWN,
            eligible_for_outreach=False,
            source=source,
            verified_at=signal.verified_at,
            reason=(
                "Open-to-work was not taken from a permitted explicit source. "
                "Resume text, job changes, employment gaps, and profile activity "
                "are never used. UNKNOWN: do not automatically contact."
            ),
        )
    if source_key not in PERMITTED_SOURCES:
        return OutreachEligibility(
            candidate_id=candidate_id,
            availability_status=OpenToWorkStatus.UNKNOWN,
            eligible_for_outreach=False,
            source=source,
            verified_at=signal.verified_at,
            reason=(
                "Source is not on the permitted explicit-signal list. "
                "UNKNOWN: do not automatically contact."
            ),
        )

    if signal.status is OpenToWorkStatus.OPEN_TO_WORK:
        return OutreachEligibility(
            candidate_id=candidate_id,
            availability_status=OpenToWorkStatus.OPEN_TO_WORK,
            eligible_for_outreach=True,
            source=source,
            verified_at=signal.verified_at,
            reason="Explicit OPEN_TO_WORK signal from a permitted source.",
        )
    if signal.status is OpenToWorkStatus.NOT_OPEN_TO_WORK:
        return OutreachEligibility(
            candidate_id=candidate_id,
            availability_status=OpenToWorkStatus.NOT_OPEN_TO_WORK,
            eligible_for_outreach=False,
            source=source,
            verified_at=signal.verified_at,
            reason=(
                "Explicit NOT_OPEN_TO_WORK signal. Not eligible for automated "
                "outreach. Candidate is retained."
            ),
        )
    return OutreachEligibility(
        candidate_id=candidate_id,
        availability_status=OpenToWorkStatus.UNKNOWN,
        eligible_for_outreach=False,
        source=source,
        verified_at=signal.verified_at,
        reason=(
            "Explicit status is UNKNOWN. Do not automatically contact. "
            "Candidate is retained."
        ),
    )


def filter_eligible_for_outreach(
    evaluations: list[OutreachEligibility],
) -> list[OutreachEligibility]:
    """Return outreach-eligible rows only. Does not delete anyone."""
    return [row for row in evaluations if row.eligible_for_outreach]
