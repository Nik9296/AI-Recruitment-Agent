"""Persistence for interview proposals."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.candidate import CandidateEvent
from app.database.models.interview import Interview


class InterviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(
        self, job_id: uuid.UUID, candidate_id: uuid.UUID
    ) -> Interview | None:
        result = await self.session.execute(
            select(Interview).where(
                Interview.job_id == job_id,
                Interview.candidate_id == candidate_id,
            )
        )
        return result.scalar_one_or_none()

    async def upsert_proposal(
        self,
        *,
        job_id: uuid.UUID,
        candidate_id: uuid.UUID,
        timezone: str,
        duration_minutes: int,
        proposed_slots: list[dict],
        recruiter_id: str | None,
    ) -> Interview:
        row = await self.get(job_id, candidate_id)
        if row is None:
            row = Interview(job_id=job_id, candidate_id=candidate_id)
            self.session.add(row)
        if row.status == "confirmed":
            return row
        row.status = "proposed"
        row.timezone = timezone
        row.duration_minutes = duration_minutes
        row.proposed_slots = proposed_slots
        row.recruiter_id = recruiter_id
        row.calendar_booked = False
        self.session.add(
            CandidateEvent(
                candidate_id=candidate_id,
                event_type="interview_proposed",
                payload={
                    "job_id": str(job_id),
                    "slot_count": len(proposed_slots),
                    "calendar_booked": False,
                    "recruiter_id": recruiter_id,
                },
            )
        )
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def confirm(
        self,
        row: Interview,
        *,
        start_at: datetime,
        end_at: datetime,
        calendar_event_id: str | None,
        calendar_booked: bool,
        recruiter_id: str | None,
    ) -> Interview:
        row.status = "confirmed"
        row.start_at = start_at
        row.end_at = end_at
        row.calendar_event_id = calendar_event_id
        row.calendar_booked = calendar_booked
        row.recruiter_id = recruiter_id
        self.session.add(
            CandidateEvent(
                candidate_id=row.candidate_id,
                event_type="interview_confirmed",
                payload={
                    "job_id": str(row.job_id),
                    "calendar_booked": calendar_booked,
                    "has_calendar_event": bool(calendar_event_id),
                    "recruiter_id": recruiter_id,
                },
            )
        )
        await self.session.commit()
        await self.session.refresh(row)
        return row
