"""Human-approval workflow service. Does not send email."""

from __future__ import annotations

import uuid

from sqlalchemy.exc import IntegrityError

from app.candidates.availability_filter import evaluate_open_to_work
from app.database.models.job_candidate import JobCandidate
from app.database.repositories.recruiter_repository import RecruiterRepository
from app.database.repositories.workflow_repository import WorkflowRepository
from app.schemas.workflow import (
    OutreachHandoffResponse,
    WorkflowHistoryResponse,
    WorkflowTransitionRecord,
)
from app.services.recruiter_service import _signal_from_candidate
from app.workflow.audit import log_outreach_handoff, log_transition
from app.workflow.outreach_gate import (
    DuplicateOutreachError,
    require_outreach_handoff,
)
from app.workflow.states import REVIEW_ACTION_TO_WORKFLOW, WorkflowState
from app.workflow.transitions import (
    RECRUITER_ACTOR,
    InvalidWorkflowTransitionError,
    validate_transition,
)


class WorkflowService:
    def __init__(
        self,
        workflow_repository: WorkflowRepository,
        recruiter_repository: RecruiterRepository,
    ) -> None:
        self.workflow_repository = workflow_repository
        self.recruiter_repository = recruiter_repository

    async def change_status(
        self,
        job_id: uuid.UUID,
        candidate_id: uuid.UUID,
        to_status: str,
        *,
        recruiter_id: str | None,
        reason: str | None = None,
        actor: str = RECRUITER_ACTOR,
    ) -> WorkflowHistoryResponse | None:
        row = await self.workflow_repository.get_job_candidate(job_id, candidate_id)
        if row is None:
            return None
        current = row.workflow_status or WorkflowState.PENDING_REVIEW.value
        _from, destination = validate_transition(current, to_status, actor=actor)
        comment = (reason or "").strip() or None
        await self.workflow_repository.add_transition(
            row,
            from_status=_from.value if _from is not None else None,
            to_status=destination.value,
            recruiter_id=recruiter_id,
            actor=actor,
            reason=comment,
        )
        log_transition(
            job_id=job_id,
            candidate_id=candidate_id,
            from_status=_from,
            to_status=destination,
            recruiter_id=recruiter_id,
            actor=actor,
            reason=comment,
        )
        await self.workflow_repository.commit()
        return await self.get_history(job_id, candidate_id)

    async def apply_review_action(
        self,
        job_id: uuid.UUID,
        candidate_id: uuid.UUID,
        review_status: str,
        *,
        recruiter_id: str | None,
        reason: str | None = None,
    ) -> WorkflowHistoryResponse | None:
        try:
            destination = REVIEW_ACTION_TO_WORKFLOW[review_status]
        except KeyError as exc:
            raise InvalidWorkflowTransitionError(
                f"Unknown review action: {review_status}"
            ) from exc
        row = await self.workflow_repository.get_job_candidate(job_id, candidate_id)
        if row is None:
            return None
        current = row.workflow_status or WorkflowState.PENDING_REVIEW.value
        # Idempotent recruiter actions: if already in the target review state,
        # return the current history instead of raising a transition error.
        if current == destination.value:
            return await self.get_history(job_id, candidate_id)
        return await self.change_status(
            job_id,
            candidate_id,
            destination.value,
            recruiter_id=recruiter_id,
            reason=reason,
            actor=RECRUITER_ACTOR,
        )

    async def record_shortlist_pipeline(self, rows: list[JobCandidate]) -> None:
        for row in rows:
            await self.workflow_repository.record_shortlist_pipeline(row)
        await self.workflow_repository.commit()

    async def get_history(
        self, job_id: uuid.UUID, candidate_id: uuid.UUID
    ) -> WorkflowHistoryResponse | None:
        row = await self.workflow_repository.get_job_candidate(job_id, candidate_id)
        if row is None:
            return None
        transitions = await self.workflow_repository.list_transitions(
            job_id, candidate_id
        )
        handoff = await self.workflow_repository.get_handoff(job_id, candidate_id)
        return WorkflowHistoryResponse(
            job_id=job_id,
            candidate_id=candidate_id,
            workflow_status=row.workflow_status,
            review_status=row.review_status,
            outreach_handed_off=handoff is not None,
            outreach_handed_off_at=row.outreach_handed_off_at,
            transitions=[
                WorkflowTransitionRecord(
                    id=item.id,
                    from_status=item.from_status,
                    to_status=item.to_status,
                    recruiter_id=item.recruiter_id,
                    actor=item.actor,
                    reason=item.reason,
                    created_at=item.created_at,
                )
                for item in transitions
            ],
        )

    async def handoff_to_outreach(
        self,
        job_id: uuid.UUID,
        candidate_id: uuid.UUID,
        *,
        recruiter_id: str,
        reason: str | None = None,
    ) -> OutreachHandoffResponse | None:
        row = await self.workflow_repository.get_job_candidate(job_id, candidate_id)
        candidate = await self.recruiter_repository.get_candidate(candidate_id)
        if row is None or candidate is None:
            return None
        eligibility = evaluate_open_to_work(
            candidate.id, _signal_from_candidate(candidate)
        )
        existing = await self.workflow_repository.get_handoff(job_id, candidate_id)
        decision = require_outreach_handoff(
            workflow_status=row.workflow_status,
            eligible_open_to_work=eligibility.eligible_for_outreach,
            already_handed_off=existing is not None,
            overall_score=row.overall_score,
        )
        try:
            handoff = await self.workflow_repository.add_handoff(
                job_id=job_id,
                candidate_id=candidate_id,
                recruiter_id=recruiter_id,
                reason=(reason or "").strip() or None,
            )
            await self.workflow_repository.commit()
        except IntegrityError as exc:
            raise DuplicateOutreachError(
                "Duplicate outreach is not allowed. No email will be sent."
            ) from exc
        log_outreach_handoff(
            job_id=job_id,
            candidate_id=candidate_id,
            recruiter_id=recruiter_id,
            allowed=True,
            reason=decision.reason,
        )
        return OutreachHandoffResponse(
            job_id=job_id,
            candidate_id=candidate_id,
            workflow_status=row.workflow_status,
            recruiter_id=recruiter_id,
            handed_off_at=handoff.created_at,
            email_sent=False,
            queued_for_outreach_agent=True,
            message=decision.reason,
        )
