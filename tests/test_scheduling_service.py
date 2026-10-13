from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from app.agents.scheduling_agent import SchedulingAgent
from app.config.settings import Settings
from app.integrations.calendar_service import CalendarService
from app.models.scheduling import InterviewSlot, SchedulingProposal
from app.schemas.scheduling import InterviewConfirmRequest
from app.services.scheduling_service import SchedulingService
from app.workflow.states import WorkflowState


def _job_row():
    row = MagicMock()
    row.job_title = "AI/ML Engineer"
    row.experience_min = 3
    row.experience_max = 8
    row.location = "Hyderabad"
    row.work_mode = "Hybrid"
    row.employment_type = "Full-time"
    row.must_have_skills = ["Python"]
    row.preferred_skills = []
    row.education = []
    row.responsibilities = []
    row.keywords = []
    return row


def _candidate_row(candidate_id):
    row = MagicMock()
    row.id = candidate_id
    row.full_name = "Rahul Sharma"
    row.email = "rahul@example.com"
    row.phone = None
    row.location = "Hyderabad"
    row.current_job_title = "ML Engineer"
    row.total_experience_years = 6
    row.skills = ["Python"]
    row.technical_skills = ["Python"]
    row.soft_skills = []
    row.education = []
    row.certifications = []
    row.companies = []
    row.previous_roles = []
    row.projects = []
    row.achievements = []
    row.industries = []
    row.notice_period = None
    row.availability = None
    row.work_authorization = None
    row.resume_summary = None
    return row


def _service(status: str, *, interview=None):
    job_id = uuid4()
    candidate_id = uuid4()
    match = MagicMock()
    match.workflow_status = status
    recruiter = MagicMock()
    recruiter.get_job = AsyncMock(return_value=_job_row())
    recruiter.get_candidate = AsyncMock(return_value=_candidate_row(candidate_id))
    recruiter.get_job_candidate = AsyncMock(return_value=match)
    interviews = MagicMock()
    interviews.get = AsyncMock(return_value=interview)
    interviews.upsert_proposal = AsyncMock()
    interviews.confirm = AsyncMock()
    workflow = MagicMock()
    workflow.change_status = AsyncMock(return_value=MagicMock())
    workflow.get_history = AsyncMock(return_value=MagicMock())
    settings = Settings(
        calendar_dry_run=True,
        calendar_provider="none",
        interview_timezone="Asia/Kolkata",
        interview_duration_minutes=45,
    )
    service = SchedulingService(
        interviews,
        recruiter,
        workflow,
        agent=SchedulingAgent(timezone="Asia/Kolkata"),
        calendar=CalendarService(dry_run=True),
        settings=settings,
    )
    return service, job_id, candidate_id, interviews, workflow


@pytest.mark.asyncio
async def test_invite_allows_recruiter_from_any_status() -> None:
    service, job_id, candidate_id, _, workflow = _service(
        WorkflowState.PENDING_REVIEW.value
    )
    await service.invite(job_id, candidate_id, recruiter_id="tester")
    workflow.change_status.assert_awaited_once()


@pytest.mark.asyncio
async def test_propose_auto_transitions_to_interview_invited() -> None:
    service, job_id, candidate_id, _, workflow = _service(WorkflowState.CONTACTED.value)
    result = await service.propose(job_id, candidate_id, recruiter_id="tester")
    assert result is not None
    workflow.change_status.assert_awaited_once()


@pytest.mark.asyncio
async def test_confirm_uses_dry_run_calendar() -> None:
    start = datetime(2026, 9, 21, 10, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    end = start.replace(hour=10, minute=45)
    interview = MagicMock()
    interview.status = "proposed"
    interview.proposed_slots = [
        {"start_at": start.isoformat(), "end_at": end.isoformat()}
    ]
    interview.job_id = uuid4()
    interview.candidate_id = uuid4()
    interview.timezone = "Asia/Kolkata"
    interview.duration_minutes = 45
    interview.start_at = start
    interview.end_at = end
    interview.calendar_event_id = "dry-run-cal-1"
    interview.calendar_booked = False
    interview.recruiter_id = "tester"
    service, job_id, candidate_id, interviews, workflow = _service(
        WorkflowState.INTERVIEW_INVITED.value, interview=interview
    )
    interviews.confirm = AsyncMock(return_value=interview)
    result = await service.confirm(
        job_id,
        candidate_id,
        InterviewConfirmRequest(start_at=start, end_at=end),
        recruiter_id="tester",
    )
    assert result.calendar_booked is False
    interviews.confirm.assert_awaited_once()
    assert interviews.confirm.await_args.kwargs["calendar_booked"] is False
    workflow.change_status.assert_awaited_once()
