import pytest

from app.workflow.states import WorkflowState
from app.workflow.transitions import (
    InvalidWorkflowTransitionError,
    RECRUITER_ACTOR,
    SYSTEM_ACTOR,
    validate_transition,
)


def test_shortlist_pipeline_is_valid_for_system() -> None:
    current = None
    for state in (
        WorkflowState.NEW,
        WorkflowState.MATCHED,
        WorkflowState.SHORTLISTED,
        WorkflowState.PENDING_REVIEW,
    ):
        current, destination = validate_transition(
            current, state, actor=SYSTEM_ACTOR
        )
        assert destination is state
        current = destination


def test_recruiter_can_approve_from_pending_review() -> None:
    current, destination = validate_transition(
        WorkflowState.PENDING_REVIEW,
        WorkflowState.APPROVED_FOR_OUTREACH,
        actor=RECRUITER_ACTOR,
    )
    assert current is WorkflowState.PENDING_REVIEW
    assert destination is WorkflowState.APPROVED_FOR_OUTREACH


@pytest.mark.parametrize(
    ("from_status", "to_status"),
    [
        (WorkflowState.NEW, WorkflowState.APPROVED_FOR_OUTREACH),
        (WorkflowState.MATCHED, WorkflowState.CONTACTED),
        (WorkflowState.PENDING_REVIEW, WorkflowState.HIRED),
        (WorkflowState.REJECTED, WorkflowState.INTERVIEW_INVITED),
        (WorkflowState.HIRED, WorkflowState.PENDING_REVIEW),
    ],
)
def test_recruiter_can_transition_flexibly(
    from_status: WorkflowState, to_status: WorkflowState
) -> None:
    current, destination = validate_transition(
        from_status, to_status, actor=RECRUITER_ACTOR
    )
    assert current is from_status
    assert destination is to_status


def test_high_score_does_not_create_a_special_transition() -> None:
    with pytest.raises(InvalidWorkflowTransitionError):
        validate_transition(
            WorkflowState.MATCHED,
            WorkflowState.CONTACTED,
            actor=SYSTEM_ACTOR,
        )


def test_contacted_is_system_only_from_approved() -> None:
    _, destination = validate_transition(
        WorkflowState.APPROVED_FOR_OUTREACH,
        WorkflowState.CONTACTED,
        actor=SYSTEM_ACTOR,
    )
    assert destination is WorkflowState.CONTACTED
    _, destination2 = validate_transition(
        WorkflowState.APPROVED_FOR_OUTREACH,
        WorkflowState.CONTACTED,
        actor=RECRUITER_ACTOR,
    )
    assert destination2 is WorkflowState.CONTACTED


def test_recruiter_can_invite_and_schedule_after_contact() -> None:
    _, invited = validate_transition(
        WorkflowState.CONTACTED,
        WorkflowState.INTERVIEW_INVITED,
        actor=RECRUITER_ACTOR,
    )
    assert invited is WorkflowState.INTERVIEW_INVITED
    _, scheduled = validate_transition(
        WorkflowState.INTERVIEW_INVITED,
        WorkflowState.INTERVIEW_SCHEDULED,
        actor=RECRUITER_ACTOR,
    )
    assert scheduled is WorkflowState.INTERVIEW_SCHEDULED


def test_recruiter_can_invite_before_contact_when_needed() -> None:
    _, destination = validate_transition(
        WorkflowState.APPROVED_FOR_OUTREACH,
        WorkflowState.INTERVIEW_INVITED,
        actor=RECRUITER_ACTOR,
    )
    assert destination is WorkflowState.INTERVIEW_INVITED
