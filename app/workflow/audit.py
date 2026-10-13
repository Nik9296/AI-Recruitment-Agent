"""Audit helpers for workflow transitions. Do not log candidate PII."""

from __future__ import annotations

import logging
from uuid import UUID

from app.workflow.states import WorkflowState
from app.workflow.transitions import RECRUITER_ACTOR

logger = logging.getLogger("app.workflow.audit")


def log_transition(
    *,
    job_id: UUID,
    candidate_id: UUID,
    from_status: WorkflowState | str | None,
    to_status: WorkflowState | str,
    recruiter_id: str | None,
    actor: str = RECRUITER_ACTOR,
    reason: str | None = None,
) -> dict:
    payload = {
        "event": "workflow_transition",
        "job_id": str(job_id),
        "candidate_id": str(candidate_id),
        "from_status": None if from_status is None else str(from_status),
        "to_status": str(to_status),
        "recruiter_id": recruiter_id,
        "actor": actor,
        "has_reason": bool(reason and reason.strip()),
    }
    logger.info("workflow_transition", extra=payload)
    return payload


def log_outreach_handoff(
    *,
    job_id: UUID,
    candidate_id: UUID,
    recruiter_id: str | None,
    allowed: bool,
    reason: str,
) -> dict:
    payload = {
        "event": "outreach_handoff",
        "job_id": str(job_id),
        "candidate_id": str(candidate_id),
        "recruiter_id": recruiter_id,
        "allowed": allowed,
        "email_sent": False,
        "reason": reason,
    }
    logger.info("outreach_handoff", extra=payload)
    return payload


def log_outreach_draft(
    *,
    job_id: UUID,
    candidate_id: UUID,
    recruiter_id: str | None,
    template: str,
) -> dict:
    payload = {
        "event": "outreach_draft",
        "job_id": str(job_id),
        "candidate_id": str(candidate_id),
        "recruiter_id": recruiter_id,
        "template": template,
        "email_sent": False,
        "review_status": "pending_recruiter_review",
    }
    logger.info("outreach_draft", extra=payload)
    return payload
