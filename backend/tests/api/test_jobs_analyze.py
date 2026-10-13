from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.core.exceptions import JDAnalysisError
from app.models.job_description import AnalyzedJobDescription


async def test_health(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_analyze_success(
    client: AsyncClient,
    analyzed_jd: AnalyzedJobDescription,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.api.v1.routes.jobs.analyze_job_description",
        AsyncMock(return_value=analyzed_jd),
    )
    response = await client.post(
        "/api/v1/jobs/analyze",
        json={
            "job_description": (
                "We are hiring a software engineer with Python and FastAPI "
                "experience in Bengaluru."
            ),
            "persist": False,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["title"] == "Software Engineer"
    assert body["job_id"] is None
    assert "model" in body
    assert "latency_ms" in body


async def test_analyze_rejects_short_jd(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/jobs/analyze",
        json={"job_description": "too short"},
    )
    assert response.status_code == 422


async def test_analyze_returns_422_when_analysis_fails(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.api.v1.routes.jobs.analyze_job_description",
        AsyncMock(side_effect=JDAnalysisError(["title: title is required"])),
    )
    response = await client.post(
        "/api/v1/jobs/analyze",
        json={
            "job_description": (
                "We are hiring someone but the description is intentionally "
                "unusable for extraction."
            )
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"]["errors"] == ["title: title is required"]
