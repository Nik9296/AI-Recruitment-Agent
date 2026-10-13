"""Human-approval workflow for outreach. Isolated from matching agents."""

from app.workflow.outreach_gate import (
    DuplicateOutreachError,
    OutreachHandoffDecision,
    OutreachHandoffDeniedError,
    evaluate_outreach_handoff,
    require_outreach_handoff,
)
from app.workflow.states import WorkflowState
from app.workflow.transitions import (
    InvalidWorkflowTransitionError,
    RECRUITER_ACTOR,
    SYSTEM_ACTOR,
    validate_transition,
)

__all__ = [
    "DuplicateOutreachError",
    "InvalidWorkflowTransitionError",
    "OutreachHandoffDecision",
    "OutreachHandoffDeniedError",
    "RECRUITER_ACTOR",
    "SYSTEM_ACTOR",
    "WorkflowState",
    "evaluate_outreach_handoff",
    "require_outreach_handoff",
    "validate_transition",
]
