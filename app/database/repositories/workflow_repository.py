"""Persistence for workflow transitions and outreach handoffs."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.candidate import CandidateEvent
from app.database.models.job_candidate import JobCandidate
from app.database.models.workflow import JobCandidateTransition, OutreachHandoff
from app.workflow.states import WORKFLOW_TO_REVIEW_STATUS, WorkflowState
from app.workflow.transitions import SYSTEM_ACTOR, validate_transition


class WorkflowRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

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

    async def list_transitions(
        self, job_id: uuid.UUID, candidate_id: uuid.UUID
    ) -> list[JobCandidateTransition]:
        result = await self.session.execute(
            select(JobCandidateTransition)
            .where(
                JobCandidateTransition.job_id == job_id,
                JobCandidateTransition.candidate_id == candidate_id,
            )
            .order_by(JobCandidateTransition.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_handoff(
        self, job_id: uuid.UUID, candidate_id: uuid.UUID
    ) -> OutreachHandoff | None:
        result = await self.session.execute(
            select(OutreachHandoff).where(
                OutreachHandoff.job_id == job_id,
                OutreachHandoff.candidate_id == candidate_id,
            )
        )
        return result.scalar_one_or_none()

    async def add_transition(
        self,
        row: JobCandidate,
        *,
        from_status: str | None,
        to_status: str,
        recruiter_id: str | None,
        actor: str,
        reason: str | None,
    ) -> JobCandidateTransition:
        transition = JobCandidateTransition(
            job_candidate_id=row.id,
            job_id=row.job_id,
            candidate_id=row.candidate_id,
            from_status=from_status,
            to_status=to_status,
            recruiter_id=recruiter_id,
            actor=actor,
            reason=reason,
        )
        self.session.add(transition)
        self.session.add(
            CandidateEvent(
                candidate_id=row.candidate_id,
                event_type="workflow_transition",
                payload={
                    "job_id": str(row.job_id),
                    "from_status": from_status,
                    "to_status": to_status,
                    "recruiter_id": recruiter_id,
                    "actor": actor,
                    "has_reason": bool(reason and reason.strip()),
                },
            )
        )
        state = WorkflowState(to_status)
        row.workflow_status = state.value
        row.review_status = WORKFLOW_TO_REVIEW_STATUS[state]
        return transition

    async def record_shortlist_pipeline(self, row: JobCandidate) -> None:
        existing = await self.list_transitions(row.job_id, row.candidate_id)
        if existing:
            return
        chain = [
            WorkflowState.NEW,
            WorkflowState.MATCHED,
            WorkflowState.SHORTLISTED,
            WorkflowState.PENDING_REVIEW,
        ]
        previous: str | None = None
        for state in chain:
            validate_transition(previous, state, actor=SYSTEM_ACTOR)
            await self.add_transition(
                row,
                from_status=previous,
                to_status=state.value,
                recruiter_id=None,
                actor=SYSTEM_ACTOR,
                reason=(
                    "Ranked shortlist recorded. This is not a hiring decision "
                    "and does not authorize outreach."
                ),
            )
            previous = state.value

    async def add_handoff(
        self,
        *,
        job_id: uuid.UUID,
        candidate_id: uuid.UUID,
        recruiter_id: str,
        reason: str | None,
    ) -> OutreachHandoff:
        handoff = OutreachHandoff(
            job_id=job_id,
            candidate_id=candidate_id,
            recruiter_id=recruiter_id,
            reason=reason,
            email_sent=False,
        )
        self.session.add(handoff)
        await self.session.flush()
        await self.session.refresh(handoff)
        row = await self.get_job_candidate(job_id, candidate_id)
        if row is not None:
            row.outreach_handed_off_at = datetime.now(UTC)
        self.session.add(
            CandidateEvent(
                candidate_id=candidate_id,
                event_type="outreach_handoff",
                payload={
                    "job_id": str(job_id),
                    "recruiter_id": recruiter_id,
                    "email_sent": False,
                    "has_reason": bool(reason and reason.strip()),
                },
            )
        )
        return handoff

    async def commit(self) -> None:
        await self.session.commit()
