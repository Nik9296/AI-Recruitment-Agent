import os
from pathlib import Path

import pytest

from app.agents.jd_agent.graph import analyze_job_description
from app.models.enums import EducationLevel, EmploymentType, WorkMode
from app.models.job_description import AnalyzedJobDescription

pytestmark = [
    pytest.mark.llm,
    pytest.mark.skipif(
        os.getenv("RUN_LIVE_LLM") != "1" or not os.getenv("GOOGLE_API_KEY"),
        reason="Set RUN_LIVE_LLM=1 and GOOGLE_API_KEY to run live LLM tests",
    ),
]

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "jds"


@pytest.mark.parametrize(
    "filename",
    [
        "full_time_onsite.txt",
        "remote_contract.txt",
        "intern.txt",
        "unstructured.txt",
        "preferred_skills.txt",
        "missing_location.txt",
    ],
)
async def test_live_jd_extraction_schema(filename: str) -> None:
    raw = (FIXTURES / filename).read_text(encoding="utf-8")
    analyzed = await analyze_job_description(raw)
    assert isinstance(analyzed, AnalyzedJobDescription)
    assert len(analyzed.title) >= 2
    assert analyzed.work_mode in WorkMode
    assert analyzed.employment_type in EmploymentType
    assert analyzed.education_level in EducationLevel or analyzed.education_level is None
    assert 0 <= analyzed.confidence <= 1
    assert isinstance(analyzed.must_have_skills, list)
    assert isinstance(analyzed.responsibilities, list)
    assert isinstance(analyzed.keywords, list)
