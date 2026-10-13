from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from app.agents.scheduling_agent import SchedulingAgent, SchedulingAgentError
from app.models.candidate import CandidateProfile
from app.models.job import JobProfile


def test_propose_weekday_slots_without_booking() -> None:
    agent = SchedulingAgent(timezone="Asia/Kolkata", duration_minutes=45)
    job_id = uuid4()
    candidate = CandidateProfile(
        candidate_id=uuid4(),
        full_name="Rahul Sharma",
        current_job_title="ML Engineer",
    )
    now = datetime(2026, 9, 18, 9, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    proposal = agent.propose(_job(), candidate, job_id=job_id, now=now)
    assert proposal.job_id == job_id
    assert proposal.candidate_id == candidate.candidate_id
    assert proposal.calendar_booked is False
    assert len(proposal.slots) == 6
    assert all(slot.end_at > slot.start_at for slot in proposal.slots)
    assert all(slot.start_at.weekday() < 5 for slot in proposal.slots)
    assert proposal.slots[0].start_at.hour in {10, 14}


def test_propose_requires_candidate_id() -> None:
    agent = SchedulingAgent()
    with pytest.raises(SchedulingAgentError, match="candidate_id"):
        agent.propose(
            _job(),
            CandidateProfile(full_name="Unknown"),
            job_id=uuid4(),
        )


def _job() -> JobProfile:
    return JobProfile(job_title="AI/ML Engineer", must_have_skills=["Python"])
