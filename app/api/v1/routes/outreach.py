"""Outreach draft and recruiter-authorized send API.

Draft routes never send email. The send route uses EmailService, not the agent.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.routes.recruiter import require_recruiter
from app.database.database import DatabaseNotConfiguredError, get_session
from app.database.repositories.email_send_repository import EmailSendRepository
from app.database.repositories.outreach_repository import OutreachRepository
from app.database.repositories.recruiter_repository import RecruiterRepository
from app.database.repositories.workflow_repository import WorkflowRepository
from app.integrations.email_service import (
    DuplicateEmailError,
    EmailConfigurationError,
    EmailSendDeniedError,
    EmailService,
)
from app.models.outreach import OutreachTemplateType
from app.schemas.email import EmailSendRequest, EmailSendResponse
from app.schemas.outreach import OutreachDraftResponse, OutreachGenerateRequest
from app.services.email_send_service import EmailSendService
from app.services.recruiter_auth import RecruiterSession
from app.services.outreach_service import OutreachService
from app.workflow.outreach_gate import OutreachHandoffDeniedError

router = APIRouter(dependencies=[Depends(require_recruiter)])


async def get_outreach_service(
    session: AsyncSession = Depends(get_session),
) -> OutreachService:
    return OutreachService(
        OutreachRepository(session), RecruiterRepository(session)
    )


async def get_email_send_service(
    session: AsyncSession = Depends(get_session),
) -> EmailSendService:
    return EmailSendService(
        EmailService.from_settings(),
        EmailSendRepository(session),
        OutreachRepository(session),
        RecruiterRepository(session),
        WorkflowRepository(session),
    )


@router.get(
    "/jobs/{job_id}/candidates/{candidate_id}/outreach",
    response_model=OutreachDraftResponse,
    summary="Load the latest outreach draft for recruiter review",
)
async def get_outreach_draft(
    job_id: UUID,
    candidate_id: UUID,
    template: OutreachTemplateType = Query(default=OutreachTemplateType.INITIAL),
    service: OutreachService = Depends(get_outreach_service),
) -> OutreachDraftResponse:
    try:
        draft = await service.get_draft(job_id, candidate_id, template=template)
    except DatabaseNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    if draft is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No outreach draft found for this job, candidate, and template",
        )
    return draft


@router.post(
    "/jobs/{job_id}/candidates/{candidate_id}/outreach",
    response_model=OutreachDraftResponse,
    summary="Generate an outreach draft (does not send email)",
)
async def generate_outreach_draft(
    job_id: UUID,
    candidate_id: UUID,
    request: OutreachGenerateRequest | None = None,
    service: OutreachService = Depends(get_outreach_service),
    recruiter: RecruiterSession = Depends(require_recruiter),
) -> OutreachDraftResponse:
    payload = request or OutreachGenerateRequest()
    try:
        draft = await service.generate_draft(
            job_id,
            candidate_id,
            recruiter_id=recruiter.username,
            template=payload.template,
        )
    except OutreachHandoffDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except DatabaseNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    if draft is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found for this job and candidate",
        )
    return draft


@router.post(
    "/jobs/{job_id}/candidates/{candidate_id}/outreach/send",
    response_model=EmailSendResponse,
    summary="Send a reviewed outreach draft (Email Service, not the agent)",
)
async def send_outreach_draft(
    job_id: UUID,
    candidate_id: UUID,
    request: EmailSendRequest | None = None,
    service: EmailSendService = Depends(get_email_send_service),
    recruiter: RecruiterSession = Depends(require_recruiter),
) -> EmailSendResponse:
    payload = request or EmailSendRequest()
    try:
        result = await service.send_draft(
            job_id,
            candidate_id,
            recruiter_id=recruiter.username,
            template=payload.template,
        )
    except DuplicateEmailError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except EmailSendDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except EmailConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
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
