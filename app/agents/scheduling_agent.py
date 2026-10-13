"""Scheduling Agent: propose interview windows. Does not book a calendar."""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from app.models.candidate import CandidateProfile
from app.models.job import JobProfile
from app.models.scheduling import InterviewSlot, SchedulingProposal

WEEKDAYS = {0, 1, 2, 3, 4}


class SchedulingAgentError(Exception):
    """Base scheduling error."""


class SchedulingAgent:
    """Offer recruiter-reviewable slots. Never auto-confirms attendance."""

    def __init__(
        self,
        *,
        timezone: str = "Asia/Kolkata",
        duration_minutes: int = 45,
        hour_options: tuple[int, ...] = (10, 14),
        days_ahead: int = 7,
    ) -> None:
        self.timezone = timezone
        self.duration_minutes = max(15, int(duration_minutes))
        self.hour_options = hour_options or (10, 14)
        self.days_ahead = max(1, int(days_ahead))

    def propose(
        self,
        job: JobProfile,
        candidate: CandidateProfile,
        *,
        job_id: UUID,
        now: datetime | None = None,
    ) -> SchedulingProposal:
        del job  # slots come from recruiter availability, not invented candidate data
        if candidate.candidate_id is None:
            raise SchedulingAgentError("candidate_id is required to propose interviews")
        zone = ZoneInfo(self.timezone)
        current = now or datetime.now(UTC)
        if current.tzinfo is None:
            current = current.replace(tzinfo=UTC)
        local_now = current.astimezone(zone)
        slots: list[InterviewSlot] = []
        day = local_now.date()
        scanned = 0
        while len(slots) < 6 and scanned < self.days_ahead + 10:
            scanned += 1
            day = day + timedelta(days=1)
            if day.weekday() not in WEEKDAYS:
                continue
            for hour in self.hour_options:
                start = datetime.combine(day, time(hour=hour), tzinfo=zone)
                if start <= local_now:
                    continue
                end = start + timedelta(minutes=self.duration_minutes)
                slots.append(
                    InterviewSlot(
                        start_at=start,
                        end_at=end,
                        timezone=self.timezone,
                    )
                )
                if len(slots) >= 6:
                    break
        return SchedulingProposal(
            candidate_id=candidate.candidate_id,
            job_id=job_id,
            slots=slots,
            duration_minutes=self.duration_minutes,
            calendar_booked=False,
            generated_at=datetime.now(UTC),
        )
