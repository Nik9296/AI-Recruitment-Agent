"""Gate for passing a candidate to the Outreach Agent.

Does not send email. A high ranking score is never sufficient.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.workflow.states import TERMINAL_OUTREACH_STATES, WorkflowState


class OutreachHandoffDeniedError(ValueError):
    """Raised when a candidate cannot be passed to outreach."""


class DuplicateOutreachError(OutreachHandoffDeniedError):
    """Raised when outreach was already queued for this job and candidate."""


class OutreachHandoffDecision(BaseModel):
    allowed: bool
    job_id: str | None = None
    candidate_id: str | None = None
    workflow_status: WorkflowState
    eligible_open_to_work: bool
    already_handed_off: bool
    email_will_be_sent: bool = False
    reason: str


def evaluate_outreach_handoff(
    *,
    workflow_status: WorkflowState | str,
    eligible_open_to_work: bool,
    already_handed_off: bool,
    overall_score: float | None = None,
) -> OutreachHandoffDecision:
    """Decide whether the Outreach Agent may receive this candidate.

    ``overall_score`` is accepted only so callers cannot accidentally treat
    ranking as approval. It is ignored.
    """
    del overall_score  # ranking is never an outreach authorization
    status = (
        workflow_status
        if isinstance(workflow_status, WorkflowState)
        else WorkflowState(workflow_status)
    )
    if not eligible_open_to_work:
        return OutreachHandoffDecision(
            allowed=False,
            workflow_status=status,
            eligible_open_to_work=False,
            already_handed_off=already_handed_off,
            reason=(
                "Candidate does not have an explicit eligible open-to-work "
                "status. No email will be sent."
            ),
        )
    if already_handed_off or status in TERMINAL_OUTREACH_STATES:
        return OutreachHandoffDecision(
            allowed=False,
            workflow_status=status,
            eligible_open_to_work=eligible_open_to_work,
            already_handed_off=True,
            reason="Duplicate outreach is not allowed. No email will be sent.",
        )
    return OutreachHandoffDecision(
        allowed=True,
        workflow_status=status,
        eligible_open_to_work=True,
        already_handed_off=False,
        email_will_be_sent=False,
        reason="Queued for the Outreach Agent. Email is not sent from this step.",
    )


def require_outreach_handoff(**kwargs) -> OutreachHandoffDecision:
    decision = evaluate_outreach_handoff(**kwargs)
    if decision.allowed:
        return decision
    if decision.already_handed_off:
        raise DuplicateOutreachError(decision.reason)
    raise OutreachHandoffDeniedError(decision.reason)
