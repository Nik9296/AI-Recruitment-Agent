from fastapi import APIRouter

from app.api.v1.routes.jobs import router as jobs_router
from app.api.v1.routes.outreach import router as outreach_router
from app.api.v1.routes.pipeline import router as pipeline_router
from app.api.v1.routes.recruiter import router as recruiter_router
from app.api.v1.routes.scheduling import router as scheduling_router

api_router = APIRouter()
api_router.include_router(jobs_router, prefix="/jobs", tags=["jobs"])
api_router.include_router(recruiter_router, prefix="/recruiter", tags=["recruiter"])
api_router.include_router(outreach_router, prefix="/recruiter", tags=["recruiter"])
api_router.include_router(pipeline_router, prefix="/recruiter", tags=["recruiter"])
api_router.include_router(scheduling_router, prefix="/recruiter", tags=["recruiter"])
