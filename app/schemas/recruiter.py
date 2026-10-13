"""Recruiter dashboard schemas. Approve/reject/hold does not send email."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.ranking import RankedCandidate

REQUIREMENT_MATCH_SOURCE = "deterministic_requirement_matching"
EXPLANATION_SOURCE = "matching_agent"
REVIEW_SOURCE = "recruiter"


class RecruiterLoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class RecruiterLoginResponse(BaseModel):
    token: str
    token_type: Literal["bearer"] = "bearer"
    username: str
    expires_at: int
    message: str = "Logged in. This session cannot send candidate email."


class RecruiterSessionResponse(BaseModel):
    username: str
    expires_at: int


class RecruiterCandidateRow(BaseModel):
    candidate_id: UUID
    name: str | None
    match_percent: int = Field(ge=0, le=100)
    availability_status: str
    eligible_for_outreach: bool
    review_status: str
    workflow_status: str = "PENDING_REVIEW"
    explanation: str
    matched_requirements: list[str]
    missing_requirements: list[str]
    confidence: float
    current_job_title: str | None = None
    location: str | None = None
    has_resume: bool = False
    requirement_match_source: Literal["deterministic_requirement_matching"] = (
        "deterministic_requirement_matching"
    )
    explanation_source: Literal["matching_agent"] = "matching_agent"
    review_source: Literal["recruiter"] = "recruiter"


class RecruiterJobSummary(BaseModel):
    job_id: UUID
    job_title: str | None
    location: str | None = None
    work_mode: str | None = None
    employment_type: str | None = None
    matched_count: int
    open_to_work_count: int
    pending_review_count: int = 0
    approved_count: int = 0
    rejected_count: int = 0
    on_hold_count: int = 0


class RecruiterDashboard(RecruiterJobSummary):
    experience_min: float | None = None
    experience_max: float | None = None
    must_have_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    candidates: list[RecruiterCandidateRow] = Field(default_factory=list)


class RecruiterDecisionResponse(BaseModel):
    job_id: UUID
    candidate_id: UUID
    review_status: str
    workflow_status: str | None = None
    review_source: Literal["recruiter"] = "recruiter"
    eligible_for_outreach: bool
    communications_sent: bool = False
    message: str


class RecordShortlistRequest(BaseModel):
    ranked: list[RankedCandidate]


class ResumeAccess(BaseModel):
    resume_id: UUID
    file_name: str | None
    source: str | None
    content_type: str | None
    byte_size: int | None
    available_on_server: bool
    download_path: str | None = None


class RecruiterCandidateProfile(BaseModel):
    job_id: UUID
    job_title: str | None
    candidate_id: UUID
    name: str | None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    current_job_title: str | None = None
    total_experience_years: float | None = None
    technical_skills: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    education: list[Any] = Field(default_factory=list)
    certifications: list[Any] = Field(default_factory=list)
    previous_roles: list[Any] = Field(default_factory=list)
    projects: list[Any] = Field(default_factory=list)
    companies: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    resume_summary: str | None = None
    resumes: list[ResumeAccess] = Field(default_factory=list)
    availability_status: str
    open_to_work_source: str | None = None
    open_to_work_verified_at: datetime | None = None
    eligible_for_outreach: bool
    match_percent: int
    requirement_match_source: Literal["deterministic_requirement_matching"] = (
        "deterministic_requirement_matching"
    )
    matched_requirements: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    explanation_source: Literal["matching_agent"] = "matching_agent"
    explanation: str
    confidence: float
    review_source: Literal["recruiter"] = "recruiter"
    review_status: str
    workflow_status: str | None = None
    communications_sent: bool = False
