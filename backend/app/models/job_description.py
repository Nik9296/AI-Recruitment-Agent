"""Canonical JD domain models and a looser LLM extraction schema."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import EducationLevel, EmploymentType, WorkMode

MAX_RESPONSIBILITIES = 25
MAX_KEYWORDS = 40
MAX_SKILLS = 40
MAX_EDUCATION = 10
MAX_NOTES = 20


def _clean_str_list(values: list[Any], *, cap: int) -> list[str]:
    seen: set[str] = set()
    cleaned: list[str] = []
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(text)
        if len(cleaned) >= cap:
            break
    return cleaned


class LocationInfo(BaseModel):
    raw: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    is_remote: bool = False

    @field_validator("raw", "city", "state", "country", mode="before")
    @classmethod
    def strip_optional(cls, value: Any) -> Any:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class ExperienceRange(BaseModel):
    min_years: float | None = None
    max_years: float | None = None
    raw: str | None = None

    @field_validator("raw", mode="before")
    @classmethod
    def strip_raw(cls, value: Any) -> Any:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value

    @field_validator("min_years", "max_years")
    @classmethod
    def years_bounds(cls, value: float | None) -> float | None:
        if value is None:
            return value
        if value < 0 or value > 50:
            raise ValueError("experience years must be between 0 and 50")
        return value

    @model_validator(mode="after")
    def min_not_greater_than_max(self) -> "ExperienceRange":
        if (
            self.min_years is not None
            and self.max_years is not None
            and self.min_years > self.max_years
        ):
            raise ValueError("min_years must be less than or equal to max_years")
        return self


class AnalyzedJobDescription(BaseModel):
    """Validated, normalized job description used by later workflow nodes."""

    model_config = ConfigDict(use_enum_values=False)

    title: str
    experience: ExperienceRange = Field(default_factory=ExperienceRange)
    location: LocationInfo = Field(default_factory=LocationInfo)
    work_mode: WorkMode = WorkMode.UNKNOWN
    employment_type: EmploymentType = EmploymentType.UNKNOWN
    must_have_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    education_level: EducationLevel | None = EducationLevel.NONE_SPECIFIED
    responsibilities: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    confidence: float = 0.5
    extraction_notes: list[str] = Field(default_factory=list)

    @field_validator("title", mode="before")
    @classmethod
    def clean_title(cls, value: Any) -> str:
        if value is None:
            raise ValueError("title is required")
        text = str(value).strip()
        if len(text) < 2:
            raise ValueError("title must be at least 2 characters")
        return text

    @field_validator("must_have_skills", "preferred_skills", mode="before")
    @classmethod
    def clean_skills(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            value = [value]
        return _clean_str_list(value, cap=MAX_SKILLS)

    @field_validator("education", mode="before")
    @classmethod
    def clean_education(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            value = [value]
        return _clean_str_list(value, cap=MAX_EDUCATION)

    @field_validator("responsibilities", mode="before")
    @classmethod
    def clean_responsibilities(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            value = [value]
        return _clean_str_list(value, cap=MAX_RESPONSIBILITIES)

    @field_validator("keywords", mode="before")
    @classmethod
    def clean_keywords(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            value = [value]
        cleaned = _clean_str_list(value, cap=MAX_KEYWORDS)
        return [item.lower() for item in cleaned]

    @field_validator("extraction_notes", mode="before")
    @classmethod
    def clean_notes(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            value = [value]
        return _clean_str_list(value, cap=MAX_NOTES)

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, value: Any) -> float:
        if value is None or value == "":
            return 0.5
        number = float(value)
        return min(1.0, max(0.0, number))

    @model_validator(mode="after")
    def preferred_disjoint_from_must_have(self) -> "AnalyzedJobDescription":
        must_have_keys = {skill.lower() for skill in self.must_have_skills}
        self.preferred_skills = [
            skill for skill in self.preferred_skills if skill.lower() not in must_have_keys
        ]
        return self


class RawLocationInfo(BaseModel):
    raw: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    is_remote: bool | None = None


class RawExperienceRange(BaseModel):
    min_years: float | None = None
    max_years: float | None = None
    raw: str | None = None


class RawJobExtraction(BaseModel):
    """Permissive schema used for LLM structured output before normalization."""

    title: str | None = None
    experience: RawExperienceRange = Field(default_factory=RawExperienceRange)
    location: RawLocationInfo = Field(default_factory=RawLocationInfo)
    work_mode: str | None = None
    employment_type: str | None = None
    must_have_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    education_level: str | None = None
    responsibilities: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    confidence: float | None = None
    extraction_notes: list[str] = Field(default_factory=list)
