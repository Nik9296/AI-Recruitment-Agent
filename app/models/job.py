"""JobProfile domain model for the JD Agent."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class WorkMode(StrEnum):
    REMOTE = "Remote"
    HYBRID = "Hybrid"
    ON_SITE = "On-site"
    FLEXIBLE = "Flexible"
    UNKNOWN = "Unknown"


class EmploymentType(StrEnum):
    FULL_TIME = "Full-time"
    PART_TIME = "Part-time"
    CONTRACT = "Contract"
    INTERNSHIP = "Internship"
    FREELANCE = "Freelance"
    UNKNOWN = "Unknown"


_WORK_MODE_ALIASES = {
    "remote": WorkMode.REMOTE,
    "hybrid": WorkMode.HYBRID,
    "on-site": WorkMode.ON_SITE,
    "onsite": WorkMode.ON_SITE,
    "on site": WorkMode.ON_SITE,
    "in-office": WorkMode.ON_SITE,
    "in office": WorkMode.ON_SITE,
    "work from office": WorkMode.ON_SITE,
    "wfo": WorkMode.ON_SITE,
    "wfh": WorkMode.REMOTE,
    "work from home": WorkMode.REMOTE,
    "flexible": WorkMode.FLEXIBLE,
    "unknown": WorkMode.UNKNOWN,
}

_EMPLOYMENT_ALIASES = {
    "full-time": EmploymentType.FULL_TIME,
    "full time": EmploymentType.FULL_TIME,
    "fulltime": EmploymentType.FULL_TIME,
    "permanent": EmploymentType.FULL_TIME,
    "fte": EmploymentType.FULL_TIME,
    "part-time": EmploymentType.PART_TIME,
    "part time": EmploymentType.PART_TIME,
    "parttime": EmploymentType.PART_TIME,
    "contract": EmploymentType.CONTRACT,
    "contractor": EmploymentType.CONTRACT,
    "internship": EmploymentType.INTERNSHIP,
    "intern": EmploymentType.INTERNSHIP,
    "freelance": EmploymentType.FREELANCE,
    "unknown": EmploymentType.UNKNOWN,
}


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


def _coerce_enum(value: Any, aliases: dict[str, Any], enum_cls: type[StrEnum]) -> Any:
    if value is None or value == "":
        return None
    if isinstance(value, enum_cls):
        return value
    key = " ".join(str(value).strip().lower().replace("_", " ").split())
    if key in aliases:
        return aliases[key]
    try:
        return enum_cls(str(value).strip())
    except ValueError as exc:
        allowed = ", ".join(member.value for member in enum_cls)
        raise ValueError(f"must be one of: {allowed}") from exc


class JobProfile(BaseModel):
    job_title: str | None = Field(
        default=None,
        description="Extracted job title, such as Senior Backend Engineer.",
    )
    experience_min: float | None = Field(
        default=None,
        ge=0,
        description="Minimum years of experience required. Null if not stated.",
    )
    experience_max: float | None = Field(
        default=None,
        ge=0,
        description="Maximum years of experience required. Null if open-ended or not stated.",
    )
    location: str | None = Field(
        default=None,
        description="Job location as stated in the description, such as Bengaluru, India.",
    )
    work_mode: WorkMode | None = Field(
        default=None,
        description="Work arrangement: Remote, Hybrid, On-site, Flexible, or Unknown.",
    )
    employment_type: EmploymentType | None = Field(
        default=None,
        description="Employment type: Full-time, Part-time, Contract, Internship, Freelance, or Unknown.",
    )
    must_have_skills: list[str] = Field(
        default_factory=list,
        description="Required skills that a candidate must have.",
    )
    preferred_skills: list[str] = Field(
        default_factory=list,
        description="Nice-to-have skills that are not strictly required.",
    )
    education: list[str] = Field(
        default_factory=list,
        description="Education requirements extracted from the job description.",
    )
    responsibilities: list[str] = Field(
        default_factory=list,
        description="Key responsibilities or duties for the role.",
    )
    keywords: list[str] = Field(
        default_factory=list,
        description="Important keywords for later matching and search.",
    )

    @field_validator("job_title", "location", mode="before")
    @classmethod
    def strip_optional_text(cls, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("work_mode", mode="before")
    @classmethod
    def coerce_work_mode(cls, value: Any) -> Any:
        return _coerce_enum(value, _WORK_MODE_ALIASES, WorkMode)

    @field_validator("employment_type", mode="before")
    @classmethod
    def coerce_employment_type(cls, value: Any) -> Any:
        return _coerce_enum(value, _EMPLOYMENT_ALIASES, EmploymentType)

    @field_validator(
        "must_have_skills",
        "preferred_skills",
        "education",
        "responsibilities",
        "keywords",
        mode="before",
    )
    @classmethod
    def clean_lists(cls, value: Any) -> list[str]:
        return _clean_str_list(value)

    @model_validator(mode="after")
    def experience_min_not_greater_than_max(self) -> "JobProfile":
        if (
            self.experience_min is not None
            and self.experience_max is not None
            and self.experience_min > self.experience_max
        ):
            raise ValueError("experience_min cannot exceed experience_max")
        return self
