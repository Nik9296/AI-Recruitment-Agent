import pytest

from app.workflow.outreach_gate import (
    DuplicateOutreachError,
    OutreachHandoffDeniedError,
    evaluate_outreach_handoff,
    require_outreach_handoff,
)
from app.workflow.states import WorkflowState


def test_open_to_work_candidate_can_handoff_from_any_workflow_state() -> None:
    decision = evaluate_outreach_handoff(
        workflow_status=WorkflowState.MATCHED,
        eligible_open_to_work=True,
        already_handed_off=False,
        overall_score=0.99,
    )
    assert decision.allowed is True
    assert decision.email_will_be_sent is False


def test_approved_without_open_to_work_is_denied() -> None:
    decision = evaluate_outreach_handoff(
        workflow_status=WorkflowState.APPROVED_FOR_OUTREACH,
        eligible_open_to_work=False,
        already_handed_off=False,
        overall_score=0.94,
    )
    assert decision.allowed is False
    assert "open-to-work" in decision.reason


def test_approved_and_open_to_work_is_queued_without_email() -> None:
    decision = evaluate_outreach_handoff(
        workflow_status=WorkflowState.APPROVED_FOR_OUTREACH,
        eligible_open_to_work=True,
        already_handed_off=False,
        overall_score=0.12,
    )
    assert decision.allowed is True
    assert decision.email_will_be_sent is False


def test_duplicate_outreach_is_denied() -> None:
    decision = evaluate_outreach_handoff(
        workflow_status=WorkflowState.APPROVED_FOR_OUTREACH,
        eligible_open_to_work=True,
        already_handed_off=True,
    )
    assert decision.allowed is False
    with pytest.raises(DuplicateOutreachError, match="Duplicate outreach"):
        require_outreach_handoff(
            workflow_status=WorkflowState.APPROVED_FOR_OUTREACH,
            eligible_open_to_work=True,
            already_handed_off=True,
        )


def test_require_raises_when_not_open_to_work() -> None:
    with pytest.raises(OutreachHandoffDeniedError, match="open-to-work"):
        require_outreach_handoff(
            workflow_status=WorkflowState.PENDING_REVIEW,
            eligible_open_to_work=False,
            already_handed_off=False,
        )
