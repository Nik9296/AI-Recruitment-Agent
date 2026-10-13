from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.database.models.candidate import Candidate
from app.database.repositories.candidate_repository import (
    CandidateRepository,
    normalize_email,
    normalize_phone_digits,
)
from app.models.candidate import CandidateProfile
from app.schemas.candidate import CandidateSearchQuery, ResumeFileRef
from app.services.candidate_service import CandidateService, DuplicateCandidateError


def _profile(**overrides) -> CandidateProfile:
    payload = {
        "full_name": "Priya Shah",
        "email": "Priya.Shah@example.com",
        "phone": "+91 98111 22334",
        "location": "Bengaluru",
        "current_job_title": "Software Engineer",
        "total_experience_years": 5,
        "technical_skills": ["Python", "k8s"],
        "soft_skills": ["Communication"],
        "skills": ["Python", "Kubernetes"],
        "education": [{"institution": "RVCE", "degree": "B.Tech"}],
        "companies": ["Nimbus Labs"],
        "resume_summary": "Backend engineer.",
        "resume_source": "upload",
        "resume_file_name": "priya.pdf",
    }
    payload.update(overrides)
    return CandidateProfile(**payload)


def _session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_repository_create_persists_profile_skills_and_file_location() -> None:
    session = _session()
    repo = CandidateRepository(session)
    profile = _profile()
    file_ref = ResumeFileRef(
        file_path="s3://resumes/priya.pdf",
        file_name="priya.pdf",
        source="upload",
        content_type="application/pdf",
        byte_size=12000,
        checksum_sha256="abc123",
    )
    candidate = await repo.create(profile, file_ref)

    session.add.assert_called_once()
    saved = session.add.call_args.args[0]
    assert saved is candidate
    assert candidate.full_name == "Priya Shah"
    assert candidate.email_normalized == "priya.shah@example.com"
    assert candidate.phone_digits == "919811122334"
    assert candidate.current_job_title == "Software Engineer"
    assert candidate.technical_skills == ["Python", "Kubernetes"]
    assert {row.canonical_name for row in candidate.skill_rows} >= {"Python", "Kubernetes"}
    assert {row.skill_kind for row in candidate.skill_rows} >= {"technical", "soft"}
    assert candidate.resumes[0].file_path == "s3://resumes/priya.pdf"
    assert not hasattr(candidate.resumes[0], "file_bytes")
    assert candidate.events[0].event_type == "created"
    assert "email" not in candidate.events[0].payload
    assert "phone" not in candidate.events[0].payload
    assert candidate.events[0].payload["file_path"] == "s3://resumes/priya.pdf"
    assert candidate.embedding is None
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(candidate)


@pytest.mark.asyncio
async def test_repository_create_does_not_store_resume_binary() -> None:
    session = _session()
    repo = CandidateRepository(session)
    candidate = await repo.create(
        _profile(),
        ResumeFileRef(file_path="/data/resumes/priya.pdf", file_name="priya.pdf"),
    )
    dump = candidate.resumes[0].__dict__
    assert "file_path" in dump
    assert b"%PDF" not in str(dump).encode()
    assert candidate.resume_summary == "Backend engineer."


@pytest.mark.asyncio
async def test_repository_get_by_id() -> None:
    session = _session()
    expected = Candidate()
    result = MagicMock()
    result.scalar_one_or_none.return_value = expected
    session.execute = AsyncMock(return_value=result)
    repo = CandidateRepository(session)
    candidate_id = uuid4()
    assert await repo.get_by_id(candidate_id) is expected
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_repository_find_duplicate_by_email() -> None:
    session = _session()
    existing = Candidate(email_normalized="priya.shah@example.com")
    result = MagicMock()
    result.scalar_one_or_none.return_value = existing
    session.execute = AsyncMock(return_value=result)
    repo = CandidateRepository(session)
    found = await repo.find_duplicate(_profile())
    assert found is existing


@pytest.mark.asyncio
async def test_repository_search_filters_by_skill_and_location() -> None:
    session = _session()
    match = Candidate(full_name="Priya Shah")
    scalars = MagicMock()
    scalars.all.return_value = [match]
    result = MagicMock()
    result.scalars.return_value = scalars
    session.execute = AsyncMock(return_value=result)
    repo = CandidateRepository(session)
    rows = await repo.search(
        CandidateSearchQuery(skill="k8s", location="Bengaluru", limit=10)
    )
    assert rows == [match]
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_repository_update_replaces_skills_and_appends_resume() -> None:
    session = _session()
    existing = Candidate(id=uuid4(), skill_rows=[], resumes=[], events=[])
    result = MagicMock()
    result.scalar_one_or_none.return_value = existing
    session.execute = AsyncMock(return_value=result)
    repo = CandidateRepository(session)
    updated = await repo.update(
        existing.id,
        _profile(technical_skills=["Python", "FastAPI"], skills=["Python", "FastAPI"]),
        ResumeFileRef(file_path="s3://resumes/priya-v2.pdf", file_name="priya-v2.pdf"),
        status="reviewed",
    )
    assert updated is existing
    assert updated.status == "reviewed"
    assert "FastAPI" in updated.technical_skills
    assert updated.resumes[-1].file_path == "s3://resumes/priya-v2.pdf"
    assert updated.events[-1].event_type == "updated"
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_service_create_delegates_when_no_duplicate() -> None:
    repo = MagicMock()
    repo.find_duplicate = AsyncMock(return_value=None)
    expected = MagicMock()
    repo.create = AsyncMock(return_value=expected)
    service = CandidateService(repo)
    profile = _profile()
    file_ref = ResumeFileRef(file_path="s3://resumes/priya.pdf")
    result = await service.create_candidate(profile, file_ref)
    assert result is expected
    repo.create.assert_awaited_once_with(profile, file_ref)


@pytest.mark.asyncio
async def test_service_create_rejects_duplicate() -> None:
    repo = MagicMock()
    repo.find_duplicate = AsyncMock(return_value=Candidate())
    repo.create = AsyncMock()
    service = CandidateService(repo)
    with pytest.raises(DuplicateCandidateError):
        await service.create_candidate(_profile())
    repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_service_update_and_get_and_search() -> None:
    repo = MagicMock()
    repo.find_duplicate = AsyncMock(return_value=None)
    updated = MagicMock()
    repo.update = AsyncMock(return_value=updated)
    repo.get_by_id = AsyncMock(return_value=None)
    repo.search = AsyncMock(return_value=[])
    service = CandidateService(repo)
    candidate_id = uuid4()
    profile = _profile()
    assert await service.update_candidate(candidate_id, profile) is updated
    assert await service.get_candidate(candidate_id) is None
    assert await service.search_candidates(CandidateSearchQuery(skill="Python")) == []
    repo.update.assert_awaited_once()
    repo.get_by_id.assert_awaited_once_with(candidate_id)
    repo.search.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_for_sourcing_returns_empty_without_skills_or_title() -> None:
    session = _session()
    repo = CandidateRepository(session)
    rows = await repo.search_for_sourcing(
        skills=[], job_title=None, location="Hyderabad"
    )
    assert rows == []
    session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_search_for_sourcing_queries_existing_rows_only() -> None:
    session = _session()
    match = Candidate(full_name="Priya Shah")
    scalars = MagicMock()
    scalars.all.return_value = [match]
    result = MagicMock()
    result.scalars.return_value = scalars
    session.execute = AsyncMock(return_value=result)
    repo = CandidateRepository(session)
    rows = await repo.search_for_sourcing(
        skills=["Python"], job_title="Engineer", location="Bengaluru"
    )
    assert rows == [match]
    session.execute.assert_awaited_once()


def test_email_and_phone_normalization() -> None:
    assert normalize_email("  Ada@Example.COM ") == "ada@example.com"
    assert normalize_email(None) is None
    assert normalize_phone_digits("+91 98111 22334") == "919811122334"
    assert normalize_phone_digits(None) is None
