from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.models.candidate import (
    CandidateProfile,
    Certification,
    EducationEntry,
    PreviousRole,
    Project,
)
from app.models.job import JobProfile


def test_empty_profile_has_safe_null_and_list_defaults() -> None:
    profile = CandidateProfile()
    assert profile.candidate_id is None
    assert profile.full_name is None
    assert profile.email is None
    assert profile.phone is None
    assert profile.location is None
    assert profile.current_job_title is None
    assert profile.total_experience_years is None
    assert profile.skills == []
    assert profile.technical_skills == []
    assert profile.soft_skills == []
    assert profile.education == []
    assert profile.certifications == []
    assert profile.companies == []
    assert profile.previous_roles == []
    assert profile.projects == []
    assert profile.achievements == []
    assert profile.industries == []
    assert profile.notice_period is None
    assert profile.availability is None
    assert profile.work_authorization is None
    assert profile.resume_summary is None
    assert profile.resume_source is None
    assert profile.resume_file_name is None


def test_list_defaults_are_not_shared_across_instances() -> None:
    first = CandidateProfile()
    second = CandidateProfile()
    first.skills.append("Python")
    assert second.skills == []


def test_valid_profile() -> None:
    candidate_id = uuid4()
    profile = CandidateProfile(
        candidate_id=candidate_id,
        full_name="  Ada Lovelace  ",
        email="Ada@Example.COM",
        phone=" +91 98765 43210 ",
        location=" Pune ",
        current_job_title=" Senior Backend Engineer ",
        total_experience_years=6,
        technical_skills=["Python", " python ", "", "FastAPI"],
        soft_skills=["Communication"],
        skills=["Python", "FastAPI"],
        education=[
            {
                "institution": " IIT Bombay ",
                "degree": " B.Tech ",
                "field": " Computer Science ",
                "start_year": 2014,
                "end_year": 2018,
            }
        ],
        certifications=[{"name": " AWS Certified Developer ", "issuer": "Amazon", "year": 2023}],
        companies=["Acme", " acme ", ""],
        previous_roles=[
            {
                "title": "Backend Engineer",
                "company": "Acme",
                "start_date": "2020-01",
                "end_date": "Present",
                "highlights": ["Built APIs", " Built APIs ", ""],
            }
        ],
        projects=[
            {
                "name": "Hiring Platform",
                "description": "Internal ATS",
                "technologies": ["Python", "python"],
            }
        ],
        achievements=["Reduced latency 40%"],
        industries=["SaaS", "saas"],
        notice_period=" 30 days ",
        availability=" Immediate ",
        work_authorization=" Indian citizen ",
        resume_summary=" Backend engineer in Pune. ",
        resume_source=" upload ",
        resume_file_name=" ada.pdf ",
    )
    assert profile.candidate_id == candidate_id
    assert profile.full_name == "Ada Lovelace"
    assert profile.email == "ada@example.com"
    assert profile.phone == "+91 98765 43210"
    assert profile.location == "Pune"
    assert profile.current_job_title == "Senior Backend Engineer"
    assert profile.technical_skills == ["Python", "FastAPI"]
    assert profile.soft_skills == ["Communication"]
    assert profile.skills == ["Python", "FastAPI"]
    assert profile.companies == ["Acme"]
    assert profile.industries == ["SaaS"]
    assert profile.notice_period == "30 days"
    assert profile.education[0].institution == "IIT Bombay"
    assert profile.previous_roles[0].highlights == ["Built APIs"]
    assert profile.projects[0].technologies == ["Python"]
    assert profile.certifications[0].name == "AWS Certified Developer"


def test_blank_optional_strings_become_null() -> None:
    profile = CandidateProfile(
        full_name="   ",
        email="",
        phone="",
        location="",
        current_job_title="  ",
        notice_period="",
        availability="",
        work_authorization="",
        resume_summary="",
        resume_source="",
        resume_file_name="",
        candidate_id="",
    )
    assert profile.full_name is None
    assert profile.email is None
    assert profile.phone is None
    assert profile.location is None
    assert profile.current_job_title is None
    assert profile.notice_period is None
    assert profile.availability is None
    assert profile.work_authorization is None
    assert profile.resume_summary is None
    assert profile.resume_source is None
    assert profile.resume_file_name is None
    assert profile.candidate_id is None


def test_null_lists_become_empty_lists() -> None:
    profile = CandidateProfile(
        skills=None,
        technical_skills=None,
        soft_skills=None,
        education=None,
        certifications=None,
        companies=None,
        previous_roles=None,
        projects=None,
        achievements=None,
        industries=None,
    )
    assert profile.skills == []
    assert profile.education == []
    assert profile.certifications == []
    assert profile.previous_roles == []
    assert profile.projects == []


def test_experience_cannot_be_negative() -> None:
    with pytest.raises(ValidationError):
        CandidateProfile(total_experience_years=-1)


def test_invalid_email_is_rejected() -> None:
    with pytest.raises(ValidationError):
        CandidateProfile(email="not-an-email")
    with pytest.raises(ValidationError):
        CandidateProfile(email="ada@")


def test_candidate_id_parses_uuid_string() -> None:
    value = "907c2305-b017-45ba-861f-1feb79e9fab4"
    profile = CandidateProfile(candidate_id=value)
    assert profile.candidate_id == UUID(value)


def test_blank_nested_entries_are_dropped() -> None:
    profile = CandidateProfile(
        education=[{}],
        certifications=[{}],
        previous_roles=[{"title": "  ", "highlights": [""]}],
        projects=[{"name": "", "technologies": []}],
    )
    assert profile.education == []
    assert profile.certifications == []
    assert profile.previous_roles == []
    assert profile.projects == []


def test_education_start_year_cannot_exceed_end_year() -> None:
    with pytest.raises(ValidationError) as exc:
        EducationEntry(start_year=2020, end_year=2018)
    assert "start_year cannot exceed end_year" in str(exc.value)


def test_certification_and_project_accept_plain_strings() -> None:
    profile = CandidateProfile(
        certifications=["AWS Certified Developer"],
        projects=["Hiring Platform"],
    )
    assert profile.certifications == [Certification(name="AWS Certified Developer")]
    assert profile.projects == [Project(name="Hiring Platform")]


def test_skills_are_filled_from_technical_and_soft_when_skills_missing() -> None:
    profile = CandidateProfile(
        technical_skills=["Python", "SQL"],
        soft_skills=["Communication", "Python"],
    )
    assert profile.skills == ["Python", "SQL", "Communication"]


def test_skills_are_not_invented_when_already_provided() -> None:
    profile = CandidateProfile(
        skills=["Python"],
        technical_skills=["Go"],
        soft_skills=["Leadership"],
    )
    assert profile.skills == ["Python"]


def test_companies_are_filled_from_previous_roles_when_missing() -> None:
    profile = CandidateProfile(
        previous_roles=[
            PreviousRole(title="Engineer", company="Acme"),
            PreviousRole(title="Intern", company="Acme"),
            PreviousRole(title="Contractor", company="Globex"),
        ]
    )
    assert profile.companies == ["Acme", "Globex"]


def test_sparse_resume_does_not_invent_identity() -> None:
    profile = CandidateProfile(
        skills=["Python"],
        resume_source="text",
    )
    assert profile.full_name is None
    assert profile.email is None
    assert profile.phone is None
    assert profile.location is None
    assert profile.current_job_title is None
    assert profile.total_experience_years is None


def test_location_and_title_types_align_with_job_profile() -> None:
    job = JobProfile(
        job_title="Backend Engineer",
        location="Pune",
        experience_min=3,
        must_have_skills=["Python"],
    )
    candidate = CandidateProfile(
        current_job_title="Backend Engineer",
        location="Pune",
        total_experience_years=3,
        skills=["Python"],
    )
    assert candidate.location == job.location
    assert candidate.current_job_title == job.job_title
    assert candidate.skills == job.must_have_skills
    assert isinstance(candidate.total_experience_years, float)
    assert isinstance(job.experience_min, float)
