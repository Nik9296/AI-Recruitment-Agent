"""Job analysis HTTP endpoints."""

import logging
import time
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.agents.jd_agent.graph import analyze_job_description
from app.core.config import get_settings
from app.core.exceptions import JDAnalysisError, LLMConfigurationError
from app.db.models.job import Job
from app.db.session import SessionLocal
from app.schemas.job import AnalyzeJobRequest, AnalyzeJobResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/analyze", response_model=AnalyzeJobResponse)
async def analyze_job(request: AnalyzeJobRequest) -> AnalyzeJobResponse:
    started = time.perf_counter()
    try:
        analyzed = await analyze_job_description(request.job_description)
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except JDAnalysisError as exc:
        raise HTTPException(status_code=422, detail={"errors": exc.errors}) from exc

    job_id: UUID | None = None
    if request.persist:
        if SessionLocal is None:
            raise HTTPException(status_code=503, detail="Database is not available")
        try:
            async with SessionLocal() as session:
                job = Job(
                    raw_text=request.job_description,
                    analyzed=analyzed.model_dump(mode="json"),
                    title=analyzed.title,
                    work_mode=analyzed.work_mode.value,
                    employment_type=analyzed.employment_type.value,
                )
                session.add(job)
                await session.commit()
                await session.refresh(job)
                job_id = job.id
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Failed to persist analyzed job")
            raise HTTPException(status_code=503, detail="Failed to persist job") from exc

    return AnalyzeJobResponse(
        data=analyzed,
        job_id=job_id,
        model=get_settings().llm_model,
        latency_ms=int((time.perf_counter() - started) * 1000),
    )
