"""Propose and confirm interviews. Recruiter confirmation required."""

from __future__ import annotations

import uuid
from datetime import datetime

from app.agents.scheduling_agent import SchedulingAgent
from app.config.settings import Settings, get_settings
from app.database.repositories.interview_repository import InterviewRepository
from app.database.repositories.recruiter_repository import RecruiterRepository
from app.integrations.calendar_service import CalendarError, CalendarService
from app.models.scheduling import SchedulingProposal
from app.schemas.scheduling import InterviewConfirmRequest, InterviewRecordResponse
from app.services.outreach_service import candidate_row_to_profile, job_row_to_profile
from app.services.workflow_service import WorkflowService
from app.workflow.states import WorkflowState
from app.workflow.transitions import RECRUITER_ACTOR


class SchedulingServiceError(ValueError):
    """Raised when scheduling is not allowed."""


class SchedulingService:
    def __init__(
        self,
        interview_repository: InterviewRepository,
        recruiter_repository: RecruiterRepository,
        workflow_service: WorkflowService,
        *,
        agent: SchedulingAgent | None = None,
        calendar: CalendarService | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.interview_repository = interview_repository
        self.recruiter_repository = recruiter_repository
        self.workflow_service = workflow_service
        self.settings = settings or get_settings()
        self.agent = agent or SchedulingAgent(
            timezone=self.settings.interview_timezone,
            duration_minutes=self.settings.interview_duration_minutes,
        )
        self.calendar = calendar or CalendarService.from_settings(self.settings)

    async def invite(
        self,
        job_id: uuid.UUID,
        candidate_id: uuid.UUID,
        *,
        recruiter_id: str,
    ):
        match = await self.recruiter_repository.get_job_candidate(job_id, candidate_id)
        if match is None:
            return None
        current = match.workflow_status or WorkflowState.PENDING_REVIEW.value
        if current == WorkflowState.INTERVIEW_INVITED.value:
            return await self.workflow_service.get_history(job_id, candidate_id)
        return await self.workflow_service.change_status(
            job_id,
            candidate_id,
            WorkflowState.INTERVIEW_INVITED.value,
            recruiter_id=recruiter_id,
            reason="Recruiter invited the candidate to interview",
            actor=RECRUITER_ACTOR,
        )

    async def propose(
        self,
        job_id: uuid.UUID,
        candidate_id: uuid.UUID,
        *,
        recruiter_id: str,
    ) -> InterviewRecordResponse | None:
        loaded = await self._load(job_id, candidate_id)
        if loaded is None:
            return None
        job, candidate, match = loaded
        status = match.workflow_status or WorkflowState.PENDING_REVIEW.value
        if status != WorkflowState.INTERVIEW_INVITED.value:
            await self.workflow_service.change_status(
                job_id,
                candidate_id,
                WorkflowState.INTERVIEW_INVITED.value,
                recruiter_id=recruiter_id,
                reason="Recruiter proposed interview times",
                actor=RECRUITER_ACTOR,
            )
        proposal = self.agent.propose(
            job_row_to_profile(job),
            candidate_row_to_profile(candidate),
            job_id=job_id,
        )
        row = await self.interview_repository.upsert_proposal(
            job_id=job_id,
            candidate_id=candidate_id,
            timezone=(
                proposal.slots[0].timezone if proposal.slots else self.agent.timezone
            ),
            duration_minutes=proposal.duration_minutes,
            proposed_slots=[slot.model_dump(mode="json") for slot in proposal.slots],
            recruiter_id=recruiter_id,
        )
        return _to_response(row, proposal)

    async def confirm(
        self,
        job_id: uuid.UUID,
        candidate_id: uuid.UUID,
        request: InterviewConfirmRequest,
        *,
        recruiter_id: str,
    ) -> InterviewRecordResponse | None:
        loaded = await self._load(job_id, candidate_id)
        if loaded is None:
            return None
        job, candidate, match = loaded
        status = match.workflow_status or WorkflowState.PENDING_REVIEW.value
        if status != WorkflowState.INTERVIEW_INVITED.value:
            await self.workflow_service.change_status(
                job_id,
                candidate_id,
                WorkflowState.INTERVIEW_INVITED.value,
                recruiter_id=recruiter_id,
                reason="Recruiter confirmed interview time",
                actor=RECRUITER_ACTOR,
            )
        existing = await self.interview_repository.get(job_id, candidate_id)
        if existing is None or existing.status == "confirmed":
            raise SchedulingServiceError(
                "Propose interview times before confirming a slot."
            )
        start = request.start_at
        end = request.end_at
        allowed = any(_slot_matches(raw, start) for raw in existing.proposed_slots or [])
        if not allowed:
            raise SchedulingServiceError(
                "Confirm a slot from the proposed list. No calendar event was created."
            )
        title = f"Interview: {job.job_title or 'Role'} / candidate"
        attendees = []
        if candidate.email:
            attendees.append(candidate.email)
        try:
            event = self.calendar.book(
                title=title,
                start_at=start,
                end_at=end,
                attendees=attendees,
            )
        except CalendarError as exc:
            raise SchedulingServiceError(str(exc)) from exc
        row = await self.interview_repository.confirm(
            existing,
            start_at=start,
            end_at=end,
            calendar_event_id=event.event_id,
            calendar_booked=event.booked,
            recruiter_id=recruiter_id,
        )
        await self.workflow_service.change_status(
            job_id,
            candidate_id,
            WorkflowState.INTERVIEW_SCHEDULED.value,
            recruiter_id=recruiter_id,
            reason="Recruiter confirmed an interview slot",
            actor=RECRUITER_ACTOR,
        )
        return _to_response(row, None)

    async def get(
        self, job_id: uuid.UUID, candidate_id: uuid.UUID
    ) -> InterviewRecordResponse | None:
        row = await self.interview_repository.get(job_id, candidate_id)
        if row is None:
            return None
        return _to_response(row, None)

    async def _load(self, job_id: uuid.UUID, candidate_id: uuid.UUID):
        job = await self.recruiter_repository.get_job(job_id)
        candidate = await self.recruiter_repository.get_candidate(candidate_id)
        match = await self.recruiter_repository.get_job_candidate(job_id, candidate_id)
        if job is None or candidate is None or match is None:
            return None
        return job, candidate, match


def _slot_matches(raw: dict, start: datetime) -> bool:
    value = raw.get("start_at") if isinstance(raw, dict) else None
    if value is None:
        return False
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None and start.tzinfo is not None:
        parsed = parsed.replace(tzinfo=start.tzinfo)
    if start.tzinfo is None and parsed.tzinfo is not None:
        start = start.replace(tzinfo=parsed.tzinfo)
    return parsed == start


def _to_response(row, proposal: SchedulingProposal | None) -> InterviewRecordResponse:
    del proposal
    return InterviewRecordResponse(
        job_id=row.job_id,
        candidate_id=row.candidate_id,
        status=row.status,
        timezone=row.timezone,
        duration_minutes=row.duration_minutes,
        proposed_slots=list(row.proposed_slots or []),
        start_at=row.start_at,
        end_at=row.end_at,
        calendar_event_id=row.calendar_event_id,
        calendar_booked=bool(row.calendar_booked),
        recruiter_id=row.recruiter_id,
        message=(
            "Interview times proposed for recruiter review. Calendar is not booked yet."
            if row.status == "proposed"
            else (
                "Interview confirmed. Calendar dry-run: not booked on a provider."
                if not row.calendar_booked
                else "Interview confirmed and calendar event created."
            )
        ),
    )
