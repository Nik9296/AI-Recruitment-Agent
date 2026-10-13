"""Pydantic helpers for candidate persistence. Not HTTP routes."""

from pydantic import BaseModel, Field, field_validator


class ResumeFileRef(BaseModel):
    """Pointer to a resume file stored outside PostgreSQL."""

    file_path: str | None = Field(
        default=None,
        description="Object-store or filesystem location. Never a file binary.",
    )
    file_name: str | None = None
    source: str | None = None
    content_type: str | None = None
    byte_size: int | None = Field(default=None, ge=0)
    checksum_sha256: str | None = None

    @field_validator("file_path", "file_name", "source", "content_type", "checksum_sha256")
    @classmethod
    def strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        return text or None


class CandidateSearchQuery(BaseModel):
    skill: str | None = None
    location: str | None = None
    job_title: str | None = None
    status: str | None = None
    name: str | None = None
    limit: int = Field(default=50, ge=1, le=200)
