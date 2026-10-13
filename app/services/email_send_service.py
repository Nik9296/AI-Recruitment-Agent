"""Dispatch a reviewed outreach draft through EmailService. Isolated from agents."""

from __future__ import annotations

import uuid

from sqlalchemy.exc import IntegrityError

from app.candidates.availability_filter import evaluate_open_to_work
from app.config.settings import Settings, get_settings
from app.database.repositories.email_send_repository import EmailSendRepository
from app.database.repositories.outreach_repository import OutreachRepository
from app.database.repositories.recruiter_repository import RecruiterRepository
from app.database.repositories.workflow_repository import WorkflowRepository
from app.integrations.email_service import (
    DuplicateEmailError,
    EmailSendDeniedError,
    EmailSendRecord,
    EmailService,
    OutboundEmail,
)
from app.models.outreach import OutreachTemplateType
from app.schemas.email import EmailSendResponse
from app.services.recruiter_service import _signal_from_candidate
from app.workflow.audit import log_transition
from app.workflow.states import WorkflowState
from app.workflow.transitions import SYSTEM_ACTOR, validate_transition


class EmailSendService:
    def __init__(
        self,
        email_service: EmailService,
        email_repository: EmailSendRepository,
        outreach_repository: OutreachRepository,
        recruiter_repository: RecruiterRepository,
        workflow_repository: WorkflowRepository,
        *,
        settings: Settings | None = None,
    ) -> None:
        self.email_service = email_service
        self.email_repository = email_repository
        self.outreach_repository = outreach_repository
        self.recruiter_repository = recruiter_repository
        self.workflow_repository = workflow_repository
        self.settings = settings or get_settings()

    async def send_draft(
        self,
        job_id: uuid.UUID,
        candidate_id: uuid.UUID,
        *,
        recruiter_id: str,
        template: OutreachTemplateType | str = OutreachTemplateType.INITIAL,
    ) -> EmailSendResponse | None:
        template_value = (
            template.value
            if isinstance(template, OutreachTemplateType)
            else OutreachTemplateType(template).value
        )
        match_row = await self.recruiter_repository.get_job_candidate(
            job_id, candidate_id
        )
        candidate = await self.recruiter_repository.get_candidate(candidate_id)
        draft = await self.outreach_repository.get_draft(
            job_id, candidate_id, template_value
        )
        if match_row is None or candidate is None:
            return None
        if draft is None:
            raise EmailSendDeniedError(
                "Generate and review an outreach draft before sending. "
                "No email will be sent."
            )
        eligibility = evaluate_open_to_work(
            candidate.id, _signal_from_candidate(candidate)
        )
        already_sent = await self.email_repository.has_blocking_send(
            job_id, candidate_id, template_value
        )
        reply_to = (self.settings.email_reply_to or "").strip() or None
        record = self.email_service.send(
            OutboundEmail(
                candidate_id=candidate_id,
                job_id=job_id,
                recipient=candidate.email or "",
                subject=draft.subject,
                body=draft.body,
                template=template_value,
                reply_to=reply_to,
            ),
            workflow_status=match_row.workflow_status
            or WorkflowState.PENDING_REVIEW.value,
            eligible_open_to_work=eligibility.eligible_for_outreach,
            already_sent=already_sent,
            overall_score=match_row.overall_score,
        )
        try:
            row = await self.email_repository.save(record, recruiter_id=recruiter_id)
        except IntegrityError as exc:
            raise DuplicateEmailError(
                "Duplicate send is not allowed for this job and candidate."
            ) from exc
        if not record.dry_run:
            await self.outreach_repository.mark_sent(draft)
            await self._mark_contacted(match_row, recruiter_id=recruiter_id)
        await self.email_repository.commit()
        return _to_response(record, recruiter_id=row.recruiter_id)

    async def _mark_contacted(self, match_row, *, recruiter_id: str) -> None:
        current = match_row.workflow_status or WorkflowState.PENDING_REVIEW.value
        if current == WorkflowState.CONTACTED.value:
            return
        _from, destination = validate_transition(
            current, WorkflowState.CONTACTED, actor=SYSTEM_ACTOR
        )
        await self.workflow_repository.add_transition(
            match_row,
            from_status=_from.value if _from is not None else None,
            to_status=destination.value,
            recruiter_id=recruiter_id,
            actor=SYSTEM_ACTOR,
            reason="Recruiter authorized email send. Provider accepted the message.",
        )
        handoff = await self.workflow_repository.get_handoff(
            match_row.job_id, match_row.candidate_id
        )
        if handoff is not None:
            handoff.email_sent = True
        log_transition(
            job_id=match_row.job_id,
            candidate_id=match_row.candidate_id,
            from_status=_from,
            to_status=destination,
            recruiter_id=recruiter_id,
            actor=SYSTEM_ACTOR,
            reason="email_send",
        )


def _to_response(
    record: EmailSendRecord, *, recruiter_id: str | None
) -> EmailSendResponse:
    actually_sent = not record.dry_run
    if record.dry_run:
        message = (
            "Dry-run only. The provider was not called and the candidate "
            "was not contacted."
        )
    else:
        message = "Email accepted by the provider. Recruiter authorized this send."
    return EmailSendResponse(
        message_id=record.message_id,
        candidate_id=record.candidate_id,
        job_id=record.job_id,
        recipient=record.recipient,
        sent_at=record.sent_at,
        delivery_status=record.delivery_status,
        template=record.template,
        provider=record.provider,
        dry_run=record.dry_run,
        email_sent=actually_sent,
        recruiter_id=recruiter_id,
        message=message,
    )
