"""CandidateProfile domain model for the Resume Agent."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

_EMAIL_CHARS = "@"


def _clean_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        value = [value]
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in value:
        if item is None:
            continue
        text = str(item).strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(text)
    return cleaned


def _strip_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _is_blank_nested(model: BaseModel) -> bool:
    for value in model.model_dump().values():
        if isinstance(value, list):
            if value:
                return False
        elif value is not None and value != "":
            return False
    return True


class EducationEntry(BaseModel):
    institution: str | None = Field(
        default=None,
        description="School, college, or university name as stated on the resume.",
    )
    degree: str | None = Field(
        default=None,
        description="Degree or qualification, such as B.Tech or MBA.",
    )
    field: str | None = Field(
        default=None,
        description="Field of study, such as Computer Science.",
    )
    start_year: int | None = Field(
        default=None,
        ge=1900,
        le=2100,
        description="Start year if stated. Null if not stated.",
    )
    end_year: int | None = Field(
        default=None,
        ge=1900,
        le=2100,
        description="End or expected year if stated. Null if not stated.",
    )

    @field_validator("institution", "degree", "field", mode="before")
    @classmethod
    def strip_text(cls, value: Any) -> str | None:
        return _strip_optional_text(value)

    @model_validator(mode="after")
    def start_year_not_after_end_year(self) -> "EducationEntry":
        if (
            self.start_year is not None
            and self.end_year is not None
            and self.start_year > self.end_year
        ):
            raise ValueError("start_year cannot exceed end_year")
        return self


class PreviousRole(BaseModel):
    title: str | None = Field(
        default=None,
        description="Role title as stated on the resume.",
    )
    company: str | None = Field(
        default=None,
        description="Employer name as stated on the resume.",
    )
    start_date: str | None = Field(
        default=None,
        description="Start date as written (for example 2021-01 or Jan 2021).",
    )
    end_date: str | None = Field(
        default=None,
        description="End date as written, or Present if still in the role.",
    )
    highlights: list[str] = Field(
        default_factory=list,
        description="Stated responsibilities or achievements for this role.",
    )

    @field_validator("title", "company", "start_date", "end_date", mode="before")
    @classmethod
    def strip_text(cls, value: Any) -> str | None:
        return _strip_optional_text(value)

    @field_validator("highlights", mode="before")
    @classmethod
    def clean_highlights(cls, value: Any) -> list[str]:
        return _clean_str_list(value)


class Project(BaseModel):
    name: str | None = Field(
        default=None,
        description="Project name as stated on the resume.",
    )
    description: str | None = Field(
        default=None,
        description="Short project description taken from the resume.",
    )
    technologies: list[str] = Field(
        default_factory=list,
        description="Technologies named for this project.",
    )

    @field_validator("name", "description", mode="before")
    @classmethod
    def strip_text(cls, value: Any) -> str | None:
        return _strip_optional_text(value)

    @field_validator("technologies", mode="before")
    @classmethod
    def clean_technologies(cls, value: Any) -> list[str]:
        return _clean_str_list(value)


class Certification(BaseModel):
    name: str | None = Field(
        default=None,
        description="Certification name as stated on the resume.",
    )
    issuer: str | None = Field(
        default=None,
        description="Issuing organization if stated.",
    )
    year: int | None = Field(
        default=None,
        ge=1900,
        le=2100,
        description="Year awarded if stated. Null if not stated.",
    )

    @field_validator("name", "issuer", mode="before")
    @classmethod
    def strip_text(cls, value: Any) -> str | None:
        return _strip_optional_text(value)


def _drop_blank_entries(items: list[Any]) -> list[Any]:
    kept: list[Any] = []
    for item in items:
        if isinstance(item, BaseModel) and _is_blank_nested(item):
            continue
        kept.append(item)
    return kept


class CandidateProfile(BaseModel):
    """Structured candidate data extracted from a resume. Missing facts stay null."""

    candidate_id: UUID | None = Field(
        default=None,
        description="Persistence identifier. Null until the profile is saved.",
    )
    full_name: str | None = Field(
        default=None,
        description="Candidate name as stated on the resume.",
    )
    email: str | None = Field(
        default=None,
        description="Email address as stated. Null if not present.",
    )
    phone: str | None = Field(
        default=None,
        description="Phone number as stated. Null if not present.",
    )
    location: str | None = Field(
        default=None,
        description="Candidate location as stated, such as Pune, India.",
    )
    current_job_title: str | None = Field(
        default=None,
        description="Current or most recent job title. Aligns with JobProfile.job_title.",
    )
    total_experience_years: float | None = Field(
        default=None,
        ge=0,
        description="Total years of experience if stated. Null if not stated.",
    )
    skills: list[str] = Field(
        default_factory=list,
        description="All named skills for later matching against JobProfile skill lists.",
    )
    technical_skills: list[str] = Field(
        default_factory=list,
        description="Technical skills stated on the resume.",
    )
    soft_skills: list[str] = Field(
        default_factory=list,
        description="Soft skills stated on the resume.",
    )
    education: list[EducationEntry] = Field(
        default_factory=list,
        description="Education history stated on the resume.",
    )
    certifications: list[Certification] = Field(
        default_factory=list,
        description="Certifications stated on the resume.",
    )
    companies: list[str] = Field(
        default_factory=list,
        description="Employer names stated on the resume.",
    )
    previous_roles: list[PreviousRole] = Field(
        default_factory=list,
        description="Work history stated on the resume.",
    )
    projects: list[Project] = Field(
        default_factory=list,
        description="Projects stated on the resume.",
    )
    achievements: list[str] = Field(
        default_factory=list,
        description="Achievements stated on the resume.",
    )
    industries: list[str] = Field(
        default_factory=list,
        description="Industries stated on the resume.",
    )
    notice_period: str | None = Field(
        default=None,
        description="Notice period as stated, such as 30 days. Null if not stated.",
    )
    availability: str | None = Field(
        default=None,
        description="Availability as stated. Null if not stated.",
    )
    work_authorization: str | None = Field(
        default=None,
        description="Work authorization as stated. Null if not stated.",
    )
    resume_summary: str | None = Field(
        default=None,
        description="Summary taken from the resume. Null if none is present.",
    )
    resume_source: str | None = Field(
        default=None,
        description="How the resume was supplied, such as upload or text. Null if unknown.",
    )
    resume_file_name: str | None = Field(
        default=None,
        description="Original file name if a file was uploaded. Null otherwise.",
    )

    @field_validator("candidate_id", mode="before")
    @classmethod
    def empty_candidate_id_is_null(cls, value: Any) -> Any:
        if value is None or value == "":
            return None
        return value

    @field_validator(
        "full_name",
        "phone",
        "location",
        "current_job_title",
        "notice_period",
        "availability",
        "work_authorization",
        "resume_summary",
        "resume_source",
        "resume_file_name",
        mode="before",
    )
    @classmethod
    def strip_optional_text(cls, value: Any) -> str | None:
        return _strip_optional_text(value)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: Any) -> str | None:
        text = _strip_optional_text(value)
        if text is None:
            return None
        email = text.lower()
        local, sep, domain = email.partition(_EMAIL_CHARS)
        if (
            not sep
            or not local
            or not domain
            or " " in email
            or domain.startswith(".")
            or domain.endswith(".")
            or "." not in domain
        ):
            raise ValueError("email must be a valid address or null")
        return email

    @field_validator(
        "skills",
        "technical_skills",
        "soft_skills",
        "companies",
        "achievements",
        "industries",
        mode="before",
    )
    @classmethod
    def clean_lists(cls, value: Any) -> list[str]:
        return _clean_str_list(value)

    @field_validator("education", mode="before")
    @classmethod
    def coerce_education(cls, value: Any) -> list[Any]:
        return _coerce_nested_list(value, EducationEntry)

    @field_validator("certifications", mode="before")
    @classmethod
    def coerce_certifications(cls, value: Any) -> list[Any]:
        return _coerce_nested_list(value, Certification, string_field="name")

    @field_validator("previous_roles", mode="before")
    @classmethod
    def coerce_previous_roles(cls, value: Any) -> list[Any]:
        return _coerce_nested_list(value, PreviousRole)

    @field_validator("projects", mode="before")
    @classmethod
    def coerce_projects(cls, value: Any) -> list[Any]:
        return _coerce_nested_list(value, Project, string_field="name")

    @model_validator(mode="after")
    def drop_blank_nested_and_fill_grounded_lists(self) -> "CandidateProfile":
        self.education = _drop_blank_entries(self.education)
        self.certifications = _drop_blank_entries(self.certifications)
        self.previous_roles = _drop_blank_entries(self.previous_roles)
        self.projects = _drop_blank_entries(self.projects)

        if not self.skills:
            self.skills = _clean_str_list(
                [*self.technical_skills, *self.soft_skills]
            )

        if not self.companies:
            self.companies = _clean_str_list(
                [role.company for role in self.previous_roles if role.company]
            )
        return self


def _coerce_nested_list(
    value: Any,
    model_cls: type[BaseModel],
    *,
    string_field: str | None = None,
) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        value = [value]
    items: list[Any] = []
    for item in value:
        if item is None or item == "":
            continue
        if isinstance(item, model_cls):
            items.append(item)
            continue
        if isinstance(item, dict):
            items.append(item)
            continue
        if string_field is not None:
            items.append({string_field: str(item).strip()})
            continue
        raise ValueError(f"invalid {model_cls.__name__} entry")
    return items
