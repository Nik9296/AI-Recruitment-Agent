"""Interview invitation and scheduling routes. Recruiter confirmation required."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.routes.recruiter import require_recruiter
from app.database.database import DatabaseNotConfiguredError, get_session
from app.database.repositories.interview_repository import InterviewRepository
from app.database.repositories.recruiter_repository import RecruiterRepository
from app.database.repositories.workflow_repository import WorkflowRepository
from app.schemas.scheduling import InterviewConfirmRequest, InterviewRecordResponse
from app.schemas.workflow import WorkflowHistoryResponse
from app.services.recruiter_auth import RecruiterSession
from app.services.scheduling_service import SchedulingService, SchedulingServiceError
from app.services.workflow_service import WorkflowService
from app.workflow.transitions import InvalidWorkflowTransitionError

router = APIRouter(dependencies=[Depends(require_recruiter)])


async def get_scheduling_service(
    session: AsyncSession = Depends(get_session),
) -> SchedulingService:
    recruiter_repository = RecruiterRepository(session)
    return SchedulingService(
        InterviewRepository(session),
        recruiter_repository,
        WorkflowService(WorkflowRepository(session), recruiter_repository),
    )


@router.post(
    "/jobs/{job_id}/candidates/{candidate_id}/interview/invite",
    response_model=WorkflowHistoryResponse,
    summary="Mark the candidate INTERVIEW_INVITED (does not book a calendar)",
)
async def invite_to_interview(
    job_id: UUID,
    candidate_id: UUID,
    service: SchedulingService = Depends(get_scheduling_service),
    recruiter: RecruiterSession = Depends(require_recruiter),
) -> WorkflowHistoryResponse:
    try:
        history = await service.invite(
            job_id, candidate_id, recruiter_id=recruiter.username
        )
    except (SchedulingServiceError, InvalidWorkflowTransitionError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except DatabaseNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    if history is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Match not found"
        )
    return history


@router.get(
    "/jobs/{job_id}/candidates/{candidate_id}/interview",
    response_model=InterviewRecordResponse,
    summary="Load the current interview proposal or confirmation",
)
async def get_interview(
    job_id: UUID,
    candidate_id: UUID,
    service: SchedulingService = Depends(get_scheduling_service),
) -> InterviewRecordResponse:
    try:
        result = await service.get(job_id, candidate_id)
    except DatabaseNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No interview record"
        )
    return result


@router.post(
    "/jobs/{job_id}/candidates/{candidate_id}/interview/proposals",
    response_model=InterviewRecordResponse,
    summary="Propose interview times for recruiter review",
)
async def propose_interview(
    job_id: UUID,
    candidate_id: UUID,
    service: SchedulingService = Depends(get_scheduling_service),
    recruiter: RecruiterSession = Depends(require_recruiter),
) -> InterviewRecordResponse:
    try:
        result = await service.propose(
            job_id, candidate_id, recruiter_id=recruiter.username
        )
    except SchedulingServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except DatabaseNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Match not found"
        )
    return result


@router.post(
    "/jobs/{job_id}/candidates/{candidate_id}/interview/confirm",
    response_model=InterviewRecordResponse,
    summary="Confirm a proposed slot (calendar dry-run by default)",
)
async def confirm_interview(
    job_id: UUID,
    candidate_id: UUID,
    request: InterviewConfirmRequest,
    service: SchedulingService = Depends(get_scheduling_service),
    recruiter: RecruiterSession = Depends(require_recruiter),
) -> InterviewRecordResponse:
    try:
        result = await service.confirm(
            job_id, candidate_id, request, recruiter_id=recruiter.username
        )
    except (SchedulingServiceError, InvalidWorkflowTransitionError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except DatabaseNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Match not found"
        )
    return result
