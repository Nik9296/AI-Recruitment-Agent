"""HTTP request schemas for job analysis and persistence."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.job import EmploymentType, JobProfile, WorkMode


class AnalyzeJobRequest(BaseModel):
    job_description: str = Field(
        ...,
        min_length=1,
        description="Raw job description text to analyze.",
        examples=[
            "QA Engineer in Pune. Hybrid, full-time. 1-3 years. "
            "Must have Selenium. Preferred: Cypress."
        ],
    )

    @field_validator("job_description")
    @classmethod
    def reject_blank_description(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("job_description cannot be empty or whitespace-only")
        return value

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "job_description": (
                        "QA Engineer in Pune. Hybrid, full-time. 1-3 years. "
                        "Must have Selenium. Preferred: Cypress."
                    )
                }
            ]
        }
    }


class SaveJobRequest(JobProfile):
    raw_job_description: str = Field(
        ...,
        min_length=1,
        description="Original job description text that was analyzed.",
    )

    @field_validator("raw_job_description")
    @classmethod
    def reject_blank_raw(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("raw_job_description cannot be empty or whitespace-only")
        return value


class SavedJobResponse(BaseModel):
    id: UUID
    job_title: str | None
    experience_min: float | None
    experience_max: float | None
    location: str | None
    work_mode: WorkMode | None
    employment_type: EmploymentType | None
    must_have_skills: list[str]
    preferred_skills: list[str]
    education: list[str]
    responsibilities: list[str]
    keywords: list[str]
    raw_job_description: str
    created_at: datetime
    updated_at: datetime
