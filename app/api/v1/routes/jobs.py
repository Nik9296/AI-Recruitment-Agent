"""Job analysis and persistence HTTP endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.jd_agent import (
    EmptyJobDescriptionError,
    JDAgent,
    JDExtractionError,
)
from app.database.database import (
    DatabaseNotConfiguredError,
    get_session,
)
from app.database.repositories.job_repository import JobRepository
from app.database.repositories.recruiter_repository import RecruiterRepository
from app.schemas.application import JobApplicationRequest, JobApplicationResponse
from app.models.job import JobProfile
from app.schemas.job import AnalyzeJobRequest, SavedJobResponse, SaveJobRequest
from app.services.job_application_service import JobApplicationService
from app.services.job_service import JobService
from app.services.llm import LLMConfigurationError

router = APIRouter()


def get_jd_agent() -> JDAgent:
    return JDAgent()


async def get_job_service(
    session: AsyncSession = Depends(get_session),
) -> JobService:
    return JobService(JobRepository(session))


async def get_job_application_service(
    session: AsyncSession = Depends(get_session),
) -> JobApplicationService:
    return JobApplicationService(session, RecruiterRepository(session))


def _saved_response(job) -> SavedJobResponse:
    return SavedJobResponse(
        id=job.id,
        job_title=job.job_title,
        experience_min=job.experience_min,
        experience_max=job.experience_max,
        location=job.location,
        work_mode=job.work_mode,
        employment_type=job.employment_type,
        must_have_skills=job.must_have_skills or [],
        preferred_skills=job.preferred_skills or [],
        education=job.education or [],
        responsibilities=job.responsibilities or [],
        keywords=job.keywords or [],
        raw_job_description=job.raw_job_description,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.post(
    "/analyze",
    response_model=JobProfile,
    status_code=status.HTTP_200_OK,
    summary="Analyze a job description",
    description=(
        "Extract a structured JobProfile from raw job-description text using "
        "the JD Agent. The model does not invent missing fields."
    ),
    responses={
        200: {"description": "Structured job profile"},
        400: {"description": "Empty or invalid job description"},
        422: {"description": "Request or extraction validation failed"},
        503: {"description": "LLM provider is not configured"},
    },
)
def analyze_job(
    request: AnalyzeJobRequest,
    agent: JDAgent = Depends(get_jd_agent),
) -> JobProfile:
    try:
        return agent.analyze(request.job_description)
    except EmptyJobDescriptionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except LLMConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except JDExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


@router.post(
    "",
    response_model=SavedJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save an analyzed job description",
    description=(
        "Persist a JobProfile and the original job description. "
        "Does not run the JD Agent."
    ),
    responses={
        201: {"description": "Job saved"},
        503: {"description": "Database is not configured"},
    },
)
async def save_job(
    request: SaveJobRequest,
    service: JobService = Depends(get_job_service),
) -> SavedJobResponse:
    profile = JobProfile.model_validate(
        request.model_dump(exclude={"raw_job_description"})
    )
    try:
        job = await service.save_analyzed_job(profile, request.raw_job_description)
    except DatabaseNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return _saved_response(job)


@router.get(
    "/{job_id}",
    response_model=SavedJobResponse,
    summary="Get a saved job",
    responses={404: {"description": "Job not found"}},
)
async def get_job(
    job_id: UUID,
    service: JobService = Depends(get_job_service),
) -> SavedJobResponse:
    try:
        job = await service.get_job(job_id)
    except DatabaseNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return _saved_response(job)


@router.post(
    "/{job_id}/apply",
    response_model=JobApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a candidate application for a job",
    responses={404: {"description": "Job not found"}},
)
async def apply_to_job(
    job_id: UUID,
    request: JobApplicationRequest,
    service: JobApplicationService = Depends(get_job_application_service),
) -> JobApplicationResponse:
    try:
        result = await service.apply(job_id, request)
    except DatabaseNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return result
