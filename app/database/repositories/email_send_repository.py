"""Persistence for outbound email send records."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.candidate import CandidateEvent
from app.database.models.email import EmailSend
from app.integrations.email_service import EmailSendRecord, is_blocking_status


class EmailSendRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(
        self,
        job_id: uuid.UUID,
        candidate_id: uuid.UUID,
        template: str,
    ) -> EmailSend | None:
        result = await self.session.execute(
            select(EmailSend).where(
                EmailSend.job_id == job_id,
                EmailSend.candidate_id == candidate_id,
                EmailSend.template == template,
            )
        )
        return result.scalar_one_or_none()

    async def has_blocking_send(
        self,
        job_id: uuid.UUID,
        candidate_id: uuid.UUID,
        template: str,
    ) -> bool:
        row = await self.get(job_id, candidate_id, template)
        return row is not None and is_blocking_status(row.delivery_status)

    async def save(
        self, record: EmailSendRecord, *, recruiter_id: str | None
    ) -> EmailSend:
        row = await self.get(record.job_id, record.candidate_id, record.template)
        if row is None:
            row = EmailSend(
                job_id=record.job_id,
                candidate_id=record.candidate_id,
                template=record.template,
            )
            self.session.add(row)
        elif is_blocking_status(row.delivery_status):
            return row
        row.message_id = record.message_id
        row.recipient = record.recipient
        row.delivery_status = record.delivery_status
        row.provider = record.provider
        row.dry_run = record.dry_run
        row.recruiter_id = recruiter_id
        row.sent_at = record.sent_at
        self.session.add(
            CandidateEvent(
                candidate_id=record.candidate_id,
                event_type="email_send",
                payload={
                    "job_id": str(record.job_id),
                    "message_id": record.message_id,
                    "delivery_status": record.delivery_status,
                    "provider": record.provider,
                    "dry_run": record.dry_run,
                    "template": record.template,
                    "recruiter_id": recruiter_id,
                    "has_recipient": True,
                },
            )
        )
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def commit(self) -> None:
        await self.session.commit()
