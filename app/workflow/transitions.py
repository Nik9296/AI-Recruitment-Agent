"""Allowed human-approval and system workflow transitions.

A high match score never authorizes a skip to outreach.
"""

from __future__ import annotations

from app.workflow.states import WorkflowState

SYSTEM_ACTOR = "system"
RECRUITER_ACTOR = "recruiter"


class InvalidWorkflowTransitionError(ValueError):
    """Raised when from_status cannot move to to_status."""


# Recruiter-driven changes.
# NOTE: Recruiters are allowed to move candidates across workflow states
# directly based on manual judgment. The static map is kept for readability,
# while runtime validation allows full recruiter flexibility.
RECRUITER_TRANSITIONS: dict[WorkflowState, frozenset[WorkflowState]] = {
    WorkflowState.NEW: frozenset(
        {
            WorkflowState.PENDING_REVIEW,
            WorkflowState.REJECTED,
            WorkflowState.ON_HOLD,
            WorkflowState.WITHDRAWN,
        }
    ),
    WorkflowState.MATCHED: frozenset(
        {
            WorkflowState.PENDING_REVIEW,
            WorkflowState.REJECTED,
            WorkflowState.ON_HOLD,
            WorkflowState.WITHDRAWN,
        }
    ),
    WorkflowState.SHORTLISTED: frozenset(
        {
            WorkflowState.PENDING_REVIEW,
            WorkflowState.REJECTED,
            WorkflowState.ON_HOLD,
            WorkflowState.WITHDRAWN,
        }
    ),
    WorkflowState.PENDING_REVIEW: frozenset(
        {
            WorkflowState.APPROVED_FOR_OUTREACH,
            WorkflowState.REJECTED,
            WorkflowState.ON_HOLD,
            WorkflowState.WITHDRAWN,
        }
    ),
    WorkflowState.ON_HOLD: frozenset(
        {
            WorkflowState.PENDING_REVIEW,
            WorkflowState.APPROVED_FOR_OUTREACH,
            WorkflowState.REJECTED,
            WorkflowState.WITHDRAWN,
        }
    ),
    WorkflowState.APPROVED_FOR_OUTREACH: frozenset(
        {
            WorkflowState.PENDING_REVIEW,
            WorkflowState.ON_HOLD,
            WorkflowState.REJECTED,
            WorkflowState.WITHDRAWN,
        }
    ),
    WorkflowState.CONTACTED: frozenset(
        {
            WorkflowState.RESPONDED,
            WorkflowState.INTERVIEW_INVITED,
            WorkflowState.ON_HOLD,
            WorkflowState.REJECTED,
            WorkflowState.WITHDRAWN,
        }
    ),
    WorkflowState.RESPONDED: frozenset(
        {
            WorkflowState.INTERVIEW_INVITED,
            WorkflowState.ON_HOLD,
            WorkflowState.REJECTED,
            WorkflowState.WITHDRAWN,
        }
    ),
    WorkflowState.INTERVIEW_INVITED: frozenset(
        {
            WorkflowState.INTERVIEW_SCHEDULED,
            WorkflowState.ON_HOLD,
            WorkflowState.REJECTED,
            WorkflowState.WITHDRAWN,
        }
    ),
    WorkflowState.INTERVIEW_SCHEDULED: frozenset(
        {
            WorkflowState.HIRED,
            WorkflowState.ON_HOLD,
            WorkflowState.REJECTED,
            WorkflowState.WITHDRAWN,
        }
    ),
    WorkflowState.HIRED: frozenset({WorkflowState.WITHDRAWN}),
    WorkflowState.REJECTED: frozenset(
        {
            WorkflowState.PENDING_REVIEW,
            WorkflowState.ON_HOLD,
            WorkflowState.WITHDRAWN,
        }
    ),
    WorkflowState.WITHDRAWN: frozenset({WorkflowState.PENDING_REVIEW}),
}

# Matching / ranking / outreach pipeline. Never recruiter-skipable to CONTACTED
# except through the outreach handoff gate.
SYSTEM_TRANSITIONS: dict[WorkflowState, frozenset[WorkflowState]] = {
    WorkflowState.NEW: frozenset(
        {
            WorkflowState.MATCHED,
            WorkflowState.SHORTLISTED,
            WorkflowState.PENDING_REVIEW,
        }
    ),
    WorkflowState.MATCHED: frozenset(
        {WorkflowState.SHORTLISTED, WorkflowState.PENDING_REVIEW}
    ),
    WorkflowState.SHORTLISTED: frozenset({WorkflowState.PENDING_REVIEW}),
    WorkflowState.APPROVED_FOR_OUTREACH: frozenset({WorkflowState.CONTACTED}),
}


def parse_state(value: str | WorkflowState) -> WorkflowState:
    try:
        return value if isinstance(value, WorkflowState) else WorkflowState(value)
    except ValueError as exc:
        raise InvalidWorkflowTransitionError(f"Unknown workflow state: {value}") from exc


def allowed_targets(
    current: WorkflowState, *, actor: str = RECRUITER_ACTOR
) -> frozenset[WorkflowState]:
    if actor != SYSTEM_ACTOR:
        return frozenset(state for state in WorkflowState if state is not current)
    return SYSTEM_TRANSITIONS.get(current, frozenset())


def validate_transition(
    from_status: str | WorkflowState | None,
    to_status: str | WorkflowState,
    *,
    actor: str = RECRUITER_ACTOR,
) -> tuple[WorkflowState | None, WorkflowState]:
    destination = parse_state(to_status)
    if from_status is None:
        if destination is not WorkflowState.NEW:
            raise InvalidWorkflowTransitionError(
                "The first recorded state must be NEW"
            )
        return None, destination
    current = parse_state(from_status)
    if current is destination:
        raise InvalidWorkflowTransitionError(
            f"Already in {current.value}; no transition recorded"
        )
    if destination not in allowed_targets(current, actor=actor):
        raise InvalidWorkflowTransitionError(
            f"Cannot transition from {current.value} to {destination.value} "
            f"as {actor}. High match scores do not authorize outreach."
        )
    return current, destination
