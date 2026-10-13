"""Persistence for recruiter-reviewable outreach drafts."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.candidate import CandidateEvent
from app.database.models.outreach import OutreachMessageRecord
from app.models.outreach import REVIEW_PENDING, OutreachMessage


class OutreachRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_draft(
        self,
        job_id: uuid.UUID,
        candidate_id: uuid.UUID,
        template: str,
    ) -> OutreachMessageRecord | None:
        result = await self.session.execute(
            select(OutreachMessageRecord).where(
                OutreachMessageRecord.job_id == job_id,
                OutreachMessageRecord.candidate_id == candidate_id,
                OutreachMessageRecord.template == template,
            )
        )
        return result.scalar_one_or_none()

    async def upsert_draft(
        self,
        message: OutreachMessage,
        *,
        recruiter_id: str | None,
    ) -> OutreachMessageRecord:
        row = await self.get_draft(
            message.job_id, message.candidate_id, message.template.value
        )
        now = datetime.now(UTC)
        if row is None:
            row = OutreachMessageRecord(
                job_id=message.job_id,
                candidate_id=message.candidate_id,
                template=message.template.value,
            )
            self.session.add(row)
        row.subject = message.subject
        row.body = message.body
        row.personalization_points = list(message.personalization_points)
        row.recruiter_id = recruiter_id
        row.review_status = REVIEW_PENDING
        row.email_sent = False
        row.generated_at = message.generated_at
        row.updated_at = now
        self.session.add(
            CandidateEvent(
                candidate_id=message.candidate_id,
                event_type="outreach_draft",
                payload={
                    "job_id": str(message.job_id),
                    "template": message.template.value,
                    "recruiter_id": recruiter_id,
                    "email_sent": False,
                    "review_status": REVIEW_PENDING,
                    "personalization_point_count": len(message.personalization_points),
                },
            )
        )
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def mark_sent(self, row: OutreachMessageRecord) -> OutreachMessageRecord:
        row.email_sent = True
        self.session.add(
            CandidateEvent(
                candidate_id=row.candidate_id,
                event_type="email_sent",
                payload={
                    "job_id": str(row.job_id),
                    "template": row.template,
                    "email_sent": True,
                },
            )
        )
        return row
