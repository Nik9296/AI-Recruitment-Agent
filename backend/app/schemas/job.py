"""HTTP request and response schemas for job analysis."""

from uuid import UUID

from pydantic import BaseModel, Field

from app.models.job_description import AnalyzedJobDescription


class AnalyzeJobRequest(BaseModel):
    job_description: str = Field(min_length=50)
    persist: bool = False


class AnalyzeJobResponse(BaseModel):
    data: AnalyzedJobDescription
    job_id: UUID | None = None
    model: str
    latency_ms: int
