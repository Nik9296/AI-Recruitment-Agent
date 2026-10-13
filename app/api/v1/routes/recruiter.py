"""Recruiter dashboard HTTP API. Decisions do not send email."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import DatabaseNotConfiguredError, get_session
from app.database.models.job_candidate import (
    REVIEW_APPROVED,
    REVIEW_ON_HOLD,
    REVIEW_REJECTED,
)
from app.database.repositories.recruiter_repository import RecruiterRepository
from app.database.repositories.workflow_repository import WorkflowRepository
from app.schemas.recruiter import (
    RecruiterCandidateProfile,
    RecruiterDashboard,
    RecruiterDecisionResponse,
    RecruiterJobSummary,
    RecruiterLoginRequest,
    RecruiterLoginResponse,
    RecruiterSessionResponse,
    RecordShortlistRequest,
)
from app.schemas.workflow import (
    OutreachHandoffResponse,
    WorkflowChangeRequest,
    WorkflowHistoryResponse,
)
from app.services.recruiter_auth import (
    InvalidRecruiterCredentialsError,
    RecruiterAuth,
    RecruiterAuthNotConfiguredError,
    RecruiterSession,
    get_recruiter_auth,
)
from app.services.recruiter_service import RecruiterService
from app.services.workflow_service import WorkflowService
from app.workflow.outreach_gate import (
    DuplicateOutreachError,
    OutreachHandoffDeniedError,
)
from app.workflow.transitions import InvalidWorkflowTransitionError

router = APIRouter()
bearer_scheme = HTTPBearer(auto_error=False)


async def get_recruiter_service(
    session: AsyncSession = Depends(get_session),
) -> RecruiterService:
    recruiter_repository = RecruiterRepository(session)
    workflow_service = WorkflowService(
        WorkflowRepository(session), recruiter_repository
    )
    return RecruiterService(recruiter_repository, workflow_service)


async def get_workflow_service(
    session: AsyncSession = Depends(get_session),
) -> WorkflowService:
    recruiter_repository = RecruiterRepository(session)
    return WorkflowService(WorkflowRepository(session), recruiter_repository)


def require_recruiter(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    auth: RecruiterAuth = Depends(get_recruiter_auth),
) -> RecruiterSession:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    session = auth.verify_token(creds.credentials)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return session


secured = APIRouter(dependencies=[Depends(require_recruiter)])


@router.post(
    "/login",
    response_model=RecruiterLoginResponse,
    summary="Recruiter login",
)
def recruiter_login(
    request: RecruiterLoginRequest,
    auth: RecruiterAuth = Depends(get_recruiter_auth),
) -> RecruiterLoginResponse:
    try:
        token = auth.login(request.username, request.password)
    except RecruiterAuthNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except InvalidRecruiterCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc
    session = auth.verify_token(token)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Session could not be issued",
        )
    return RecruiterLoginResponse(
        token=token, username=session.username, expires_at=session.expires_at
    )


@secured.get(
    "/me",
    response_model=RecruiterSessionResponse,
    summary="Current recruiter session",
)
def recruiter_me(
    session: RecruiterSession = Depends(require_recruiter),
) -> RecruiterSessionResponse:
    return RecruiterSessionResponse(
        username=session.username, expires_at=session.expires_at
    )


@secured.get(
    "/jobs",
    response_model=list[RecruiterJobSummary],
    summary="List jobs for the recruiter dashboard",
)
async def list_recruiter_jobs(
    service: RecruiterService = Depends(get_recruiter_service),
) -> list[RecruiterJobSummary]:
    try:
        return await service.list_job_summaries()
    except DatabaseNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc


@secured.get(
    "/jobs/{job_id}",
    response_model=RecruiterDashboard,
    summary="Job details and recruiter shortlist",
    responses={404: {"description": "Job not found"}},
)
async def get_recruiter_job(
    job_id: UUID,
    query: str | None = Query(default=None, description="Search name, title, location"),
    availability: str | None = Query(
        default="all",
        description="open_to_work, not_open_to_work, unknown, or all",
    ),
    review_status: str | None = Query(
        default="all",
        description="pending, approved, rejected, on_hold, or all",
    ),
    sort: str = Query(default="match_score"),
    sort_dir: str = Query(default="desc"),
    service: RecruiterService = Depends(get_recruiter_service),
) -> RecruiterDashboard:
    try:
        dashboard = await service.get_dashboard(
            job_id,
            query=query,
            availability=availability,
            review_status=review_status,
            sort=sort,
            sort_dir=sort_dir,
        )
    except DatabaseNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    if dashboard is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return dashboard


@secured.post(
    "/jobs/{job_id}/shortlist",
    response_model=RecruiterDashboard,
    summary="Store a ranked shortlist for recruiter review",
)
async def record_shortlist(
    job_id: UUID,
    request: RecordShortlistRequest,
    service: RecruiterService = Depends(get_recruiter_service),
) -> RecruiterDashboard:
    try:
        dashboard = await service.record_shortlist(job_id, request.ranked)
    except DatabaseNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    if dashboard is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return dashboard


@secured.get(
    "/jobs/{job_id}/candidates/{candidate_id}",
    response_model=RecruiterCandidateProfile,
    summary="Candidate profile, match evidence, and recruiter status",
)
async def get_candidate_profile(
    job_id: UUID,
    candidate_id: UUID,
    service: RecruiterService = Depends(get_recruiter_service),
) -> RecruiterCandidateProfile:
    try:
        profile = await service.get_candidate_profile(job_id, candidate_id)
    except DatabaseNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate or match not found for this job",
        )
    return profile


@secured.get(
    "/candidates/{candidate_id}/resumes/{resume_id}/file",
    summary="Download a stored resume file when it exists on this server",
)
async def download_resume(
    candidate_id: UUID,
    resume_id: UUID,
    service: RecruiterService = Depends(get_recruiter_service),
) -> FileResponse:
    try:
        stored = await service.get_resume_file(candidate_id, resume_id)
    except DatabaseNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    if stored is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume file is not available on this server",
        )
    path, file_name = stored
    return FileResponse(
        path=path,
        filename=file_name or path.name,
        media_type="application/octet-stream",
    )


@secured.post(
    "/jobs/{job_id}/candidates/{candidate_id}/approve",
    response_model=RecruiterDecisionResponse,
    summary="Approve a candidate for later outreach (does not send email)",
)
async def approve_candidate(
    job_id: UUID,
    candidate_id: UUID,
    reason: str | None = Query(default=None),
    service: RecruiterService = Depends(get_recruiter_service),
    recruiter: RecruiterSession = Depends(require_recruiter),
) -> RecruiterDecisionResponse:
    return await _decide(
        service,
        job_id,
        candidate_id,
        REVIEW_APPROVED,
        recruiter_id=recruiter.username,
        reason=reason,
    )


@secured.post(
    "/jobs/{job_id}/candidates/{candidate_id}/reject",
    response_model=RecruiterDecisionResponse,
    summary="Reject a candidate (does not send email)",
)
async def reject_candidate(
    job_id: UUID,
    candidate_id: UUID,
    reason: str | None = Query(default=None),
    service: RecruiterService = Depends(get_recruiter_service),
    recruiter: RecruiterSession = Depends(require_recruiter),
) -> RecruiterDecisionResponse:
    return await _decide(
        service,
        job_id,
        candidate_id,
        REVIEW_REJECTED,
        recruiter_id=recruiter.username,
        reason=reason,
    )


@secured.post(
    "/jobs/{job_id}/candidates/{candidate_id}/hold",
    response_model=RecruiterDecisionResponse,
    summary="Put a candidate on hold (does not send email)",
)
async def hold_candidate(
    job_id: UUID,
    candidate_id: UUID,
    reason: str | None = Query(default=None),
    service: RecruiterService = Depends(get_recruiter_service),
    recruiter: RecruiterSession = Depends(require_recruiter),
) -> RecruiterDecisionResponse:
    return await _decide(
        service,
        job_id,
        candidate_id,
        REVIEW_ON_HOLD,
        recruiter_id=recruiter.username,
        reason=reason,
    )


@secured.get(
    "/jobs/{job_id}/candidates/{candidate_id}/workflow",
    response_model=WorkflowHistoryResponse,
    summary="Workflow status and transition history",
)
async def get_workflow_history(
    job_id: UUID,
    candidate_id: UUID,
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowHistoryResponse:
    try:
        history = await service.get_history(job_id, candidate_id)
    except DatabaseNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    if history is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found for this job and candidate",
        )
    return history


@secured.post(
    "/jobs/{job_id}/candidates/{candidate_id}/workflow",
    response_model=WorkflowHistoryResponse,
    summary="Change workflow status (does not send email)",
)
async def change_workflow_status(
    job_id: UUID,
    candidate_id: UUID,
    request: WorkflowChangeRequest,
    service: WorkflowService = Depends(get_workflow_service),
    recruiter: RecruiterSession = Depends(require_recruiter),
) -> WorkflowHistoryResponse:
    try:
        history = await service.change_status(
            job_id,
            candidate_id,
            request.to_status,
            recruiter_id=recruiter.username,
            reason=request.reason,
        )
    except InvalidWorkflowTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except DatabaseNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    if history is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found for this job and candidate",
        )
    return history


@secured.post(
    "/jobs/{job_id}/candidates/{candidate_id}/outreach-handoff",
    response_model=OutreachHandoffResponse,
    summary="Queue an approved candidate for the Outreach Agent (does not send email)",
)
async def outreach_handoff(
    job_id: UUID,
    candidate_id: UUID,
    reason: str | None = Query(default=None),
    service: WorkflowService = Depends(get_workflow_service),
    recruiter: RecruiterSession = Depends(require_recruiter),
) -> OutreachHandoffResponse:
    try:
        result = await service.handoff_to_outreach(
            job_id,
            candidate_id,
            recruiter_id=recruiter.username,
            reason=reason,
        )
    except DuplicateOutreachError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except OutreachHandoffDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except DatabaseNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found for this job and candidate",
        )
    return result


async def _decide(
    service: RecruiterService,
    job_id: UUID,
    candidate_id: UUID,
    review_status: str,
    *,
    recruiter_id: str | None = None,
    reason: str | None = None,
) -> RecruiterDecisionResponse:
    try:
        result = await service.decide(
            job_id,
            candidate_id,
            review_status,
            recruiter_id=recruiter_id,
            reason=reason,
        )
    except InvalidWorkflowTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except DatabaseNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found for this job and candidate",
        )
    return result


router.include_router(secured)
