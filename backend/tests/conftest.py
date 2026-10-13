from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.enums import EducationLevel, EmploymentType, WorkMode
from app.models.job_description import AnalyzedJobDescription, ExperienceRange, LocationInfo


@pytest.fixture
def analyzed_jd() -> AnalyzedJobDescription:
    return AnalyzedJobDescription(
        title="Software Engineer",
        experience=ExperienceRange(min_years=3, max_years=5, raw="3-5 years"),
        location=LocationInfo(raw="Bengaluru, India", city="Bengaluru", country="India"),
        work_mode=WorkMode.HYBRID,
        employment_type=EmploymentType.FULL_TIME,
        must_have_skills=["Python", "FastAPI"],
        preferred_skills=["Go"],
        education=["Bachelor's in Computer Science"],
        education_level=EducationLevel.BACHELORS,
        responsibilities=["Build APIs", "Review code"],
        keywords=["python", "fastapi"],
        confidence=0.9,
        extraction_notes=[],
    )


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client
