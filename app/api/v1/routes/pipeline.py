"""Sourcing and LangGraph pipeline routes. Stop at recruiter review."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.routes.recruiter import require_recruiter
from app.database.database import DatabaseNotConfiguredError, get_session
from app.database.repositories.candidate_repository import CandidateRepository
from app.database.repositories.recruiter_repository import RecruiterRepository
from app.graphs.recruitment import RecruitmentPipeline, build_default_pipeline
from app.schemas.pipeline import PipelineRunResponse, SourcingResponse
from app.services.recruiter_auth import RecruiterSession
from app.services.sourcing_service import SourcingService

router = APIRouter(dependencies=[Depends(require_recruiter)])


async def get_sourcing_service(
    session: AsyncSession = Depends(get_session),
) -> SourcingService:
    return SourcingService(CandidateRepository(session), RecruiterRepository(session))


async def get_pipeline(
    session: AsyncSession = Depends(get_session),
) -> RecruitmentPipeline:
    return build_default_pipeline(session)


@router.post(
    "/jobs/{job_id}/source",
    response_model=SourcingResponse,
    summary="Source existing ATS candidates for a job (does not invent people)",
)
async def source_job(
    job_id: UUID,
    service: SourcingService = Depends(get_sourcing_service),
    recruiter: RecruiterSession = Depends(require_recruiter),
) -> SourcingResponse:
    del recruiter
    try:
        result = await service.source_job(job_id)
    except DatabaseNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return SourcingResponse(
        job_id=job_id,
        job_title=result.job_title,
        queries=result.queries,
        candidates=result.candidates,
        invented_candidates=False,
    )


@router.post(
    "/jobs/{job_id}/pipeline/run",
    response_model=PipelineRunResponse,
    summary="Run sourcing, matching, and ranking. Stops for recruiter review.",
)
async def run_pipeline(
    job_id: UUID,
    pipeline: RecruitmentPipeline = Depends(get_pipeline),
    recruiter: RecruiterSession = Depends(require_recruiter),
) -> PipelineRunResponse:
    del recruiter
    try:
        state = await pipeline.run(job_id)
    except DatabaseNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    errors = list(state.get("errors") or [])
    if errors and errors[0] == "Job not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return PipelineRunResponse(
        job_id=job_id,
        sourced_count=int(state.get("sourced_count") or 0),
        matched_count=int(state.get("matched_count") or 0),
        ranked_count=int(state.get("ranked_count") or 0),
        shortlist_recorded=bool(state.get("shortlist_recorded")),
        outreach_sent=False,
        hired=False,
        errors=errors,
        message=(
            "Shortlist recorded for recruiter review. No email was sent and no hire was made."
            if state.get("shortlist_recorded")
            else "Pipeline finished without a new shortlist. No email was sent and no hire was made."
        ),
    )
