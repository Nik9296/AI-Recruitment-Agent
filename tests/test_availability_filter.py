from datetime import UTC, datetime
from uuid import uuid4

from app.candidates.availability_filter import (
    OpenToWorkSignal,
    OpenToWorkStatus,
    evaluate_open_to_work,
    filter_eligible_for_outreach,
)

VERIFIED_AT = datetime(2026, 9, 17, 10, 0, tzinfo=UTC)


def test_open_to_work_is_eligible() -> None:
    candidate_id = uuid4()
    result = evaluate_open_to_work(
        candidate_id,
        OpenToWorkSignal(
            status=OpenToWorkStatus.OPEN_TO_WORK,
            source="candidate_declaration",
            verified_at=VERIFIED_AT,
        ),
    )
    assert result.candidate_id == candidate_id
    assert result.availability_status is OpenToWorkStatus.OPEN_TO_WORK
    assert result.eligible_for_outreach is True
    assert result.source == "candidate_declaration"
    assert result.verified_at == VERIFIED_AT
    assert "OPEN_TO_WORK" in result.reason


def test_not_open_to_work_is_not_eligible_but_not_deleted() -> None:
    candidate_id = uuid4()
    result = evaluate_open_to_work(
        candidate_id,
        OpenToWorkSignal(
            status=OpenToWorkStatus.NOT_OPEN_TO_WORK,
            source="recruiter_recorded",
            verified_at=VERIFIED_AT,
        ),
    )
    assert result.availability_status is OpenToWorkStatus.NOT_OPEN_TO_WORK
    assert result.eligible_for_outreach is False
    assert result.source == "recruiter_recorded"
    assert result.verified_at == VERIFIED_AT
    assert "retained" in result.reason.lower()


def test_unknown_is_not_automatically_contacted() -> None:
    candidate_id = uuid4()
    result = evaluate_open_to_work(
        candidate_id,
        OpenToWorkSignal(
            status=OpenToWorkStatus.UNKNOWN,
            source="ats_open_to_work",
            verified_at=VERIFIED_AT,
        ),
    )
    assert result.availability_status is OpenToWorkStatus.UNKNOWN
    assert result.eligible_for_outreach is False
    assert result.source == "ats_open_to_work"
    assert result.verified_at == VERIFIED_AT
    assert "do not automatically contact" in result.reason.lower()


def test_missing_signal_is_unknown() -> None:
    result = evaluate_open_to_work(uuid4(), None)
    assert result.availability_status is OpenToWorkStatus.UNKNOWN
    assert result.eligible_for_outreach is False
    assert result.source is None
    assert result.verified_at is None


def test_resume_and_indirect_signals_are_never_used() -> None:
    verified = VERIFIED_AT
    for source in (
        "resume",
        "notice_period",
        "job_change",
        "employment_gap",
        "profile_activity",
        "inferred",
    ):
        result = evaluate_open_to_work(
            uuid4(),
            OpenToWorkSignal(
                status=OpenToWorkStatus.OPEN_TO_WORK,
                source=source,
                verified_at=verified,
            ),
        )
        assert result.availability_status is OpenToWorkStatus.UNKNOWN
        assert result.eligible_for_outreach is False
        assert result.source == source
        assert result.verified_at == verified


def test_filter_excludes_ineligible_without_dropping_the_full_set() -> None:
    open_id = uuid4()
    closed_id = uuid4()
    unknown_id = uuid4()
    rows = [
        evaluate_open_to_work(
            open_id,
            OpenToWorkSignal(
                status=OpenToWorkStatus.OPEN_TO_WORK,
                source="linkedin_open_to_work",
                verified_at=VERIFIED_AT,
            ),
        ),
        evaluate_open_to_work(
            closed_id,
            OpenToWorkSignal(
                status=OpenToWorkStatus.NOT_OPEN_TO_WORK,
                source="candidate_declaration",
                verified_at=VERIFIED_AT,
            ),
        ),
        evaluate_open_to_work(unknown_id, None),
    ]
    eligible = filter_eligible_for_outreach(rows)
    assert [row.candidate_id for row in eligible] == [open_id]
    assert {row.candidate_id for row in rows} == {open_id, closed_id, unknown_id}


def test_evaluation_is_deterministic() -> None:
    candidate_id = uuid4()
    signal = OpenToWorkSignal(
        status=OpenToWorkStatus.OPEN_TO_WORK,
        source="candidate_declaration",
        verified_at=VERIFIED_AT,
    )
    first = evaluate_open_to_work(candidate_id, signal)
    second = evaluate_open_to_work(candidate_id, signal)
    assert first == second
