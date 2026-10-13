import pytest
from pydantic import ValidationError

from app.models.job import EmploymentType, JobProfile, WorkMode


def test_empty_profile_has_safe_list_defaults() -> None:
    profile = JobProfile()
    assert profile.job_title is None
    assert profile.experience_min is None
    assert profile.experience_max is None
    assert profile.location is None
    assert profile.work_mode is None
    assert profile.employment_type is None
    assert profile.must_have_skills == []
    assert profile.preferred_skills == []
    assert profile.education == []
    assert profile.responsibilities == []
    assert profile.keywords == []


def test_list_defaults_are_not_shared_across_instances() -> None:
    first = JobProfile()
    second = JobProfile()
    first.must_have_skills.append("Python")
    assert second.must_have_skills == []


def test_valid_profile() -> None:
    profile = JobProfile(
        job_title="  Senior Backend Engineer  ",
        experience_min=5,
        experience_max=8,
        location=" Bengaluru ",
        work_mode="hybrid",
        employment_type="full-time",
        must_have_skills=["Python", " python ", "", "FastAPI"],
        preferred_skills=["Go"],
        education=["Bachelor's in CS"],
        responsibilities=["Design APIs"],
        keywords=["python", "Python", "api"],
    )
    assert profile.job_title == "Senior Backend Engineer"
    assert profile.location == "Bengaluru"
    assert profile.work_mode is WorkMode.HYBRID
    assert profile.employment_type is EmploymentType.FULL_TIME
    assert profile.must_have_skills == ["Python", "FastAPI"]
    assert profile.keywords == ["python", "api"]


def test_blank_optional_strings_become_null() -> None:
    profile = JobProfile(job_title="   ", location="")
    assert profile.job_title is None
    assert profile.location is None


def test_experience_cannot_be_negative() -> None:
    with pytest.raises(ValidationError):
        JobProfile(experience_min=-1)
    with pytest.raises(ValidationError):
        JobProfile(experience_max=-0.5)


def test_experience_min_cannot_exceed_max() -> None:
    with pytest.raises(ValidationError) as exc:
        JobProfile(experience_min=8, experience_max=3)
    assert "experience_min cannot exceed experience_max" in str(exc.value)


def test_experience_min_only_or_max_only_is_allowed() -> None:
    assert JobProfile(experience_min=5).experience_max is None
    assert JobProfile(experience_max=10).experience_min is None


def test_work_mode_values() -> None:
    assert JobProfile(work_mode="Remote").work_mode is WorkMode.REMOTE
    assert JobProfile(work_mode="On-site").work_mode is WorkMode.ON_SITE
    assert JobProfile(work_mode="onsite").work_mode is WorkMode.ON_SITE
    assert JobProfile(work_mode="Flexible").work_mode is WorkMode.FLEXIBLE
    assert JobProfile(work_mode="Unknown").work_mode is WorkMode.UNKNOWN


def test_invalid_work_mode_is_rejected() -> None:
    with pytest.raises(ValidationError):
        JobProfile(work_mode="office-only")


def test_employment_type_values() -> None:
    assert JobProfile(employment_type="Part-time").employment_type is EmploymentType.PART_TIME
    assert JobProfile(employment_type="Contract").employment_type is EmploymentType.CONTRACT
    assert JobProfile(employment_type="Internship").employment_type is EmploymentType.INTERNSHIP
    assert JobProfile(employment_type="Freelance").employment_type is EmploymentType.FREELANCE
    assert JobProfile(employment_type="intern").employment_type is EmploymentType.INTERNSHIP


def test_invalid_employment_type_is_rejected() -> None:
    with pytest.raises(ValidationError):
        JobProfile(employment_type="permanent-plus")


def test_null_enums_and_lists_are_accepted() -> None:
    profile = JobProfile(
        work_mode=None,
        employment_type=None,
        must_have_skills=None,
        preferred_skills=None,
        education=None,
        responsibilities=None,
        keywords=None,
    )
    assert profile.work_mode is None
    assert profile.employment_type is None
    assert profile.must_have_skills == []
    assert profile.preferred_skills == []
