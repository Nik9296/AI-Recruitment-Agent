"""Seed the recruiter dashboard demo job and three open-to-work candidates."""

from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.candidates.availability_filter import OpenToWorkStatus
from app.config.settings import get_settings
from app.database import database as db
from app.database.models.candidate import Candidate, CandidateResume
from app.database.models.job import Job
from app.database.models.job_candidate import REVIEW_PENDING, JobCandidate

JOB_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
VERIFIED_AT = datetime(2026, 9, 17, 10, 0, tzinfo=UTC)

DEMO = [
    {
        "id": uuid.UUID("22222222-2222-2222-2222-222222222221"),
        "full_name": "Rahul Sharma",
        "email": "rahul.sharma@example.com",
        "current_job_title": "ML Engineer",
        "location": "Hyderabad",
        "score": 0.94,
        "skills": ["Python", "TensorFlow", "PyTorch"],
        "matched": [
            "Required skill: Python",
            "Required skill: TensorFlow",
            "Required skill: PyTorch",
        ],
        "missing": [],
        "resume_name": "rahul_sharma.pdf",
    },
    {
        "id": uuid.UUID("22222222-2222-2222-2222-222222222222"),
        "full_name": "Amit Patel",
        "email": "amit.patel@example.com",
        "current_job_title": "AI Engineer",
        "location": "Bengaluru",
        "score": 0.91,
        "skills": ["Python", "PyTorch", "Kubernetes"],
        "matched": [
            "Required skill: Python",
            "Required skill: PyTorch",
            "Preferred skill: Kubernetes",
        ],
        "missing": ["Required skill: TensorFlow"],
        "resume_name": "amit_patel.pdf",
    },
    {
        "id": uuid.UUID("22222222-2222-2222-2222-222222222223"),
        "full_name": "Sneha Joshi",
        "email": "sneha.joshi@example.com",
        "current_job_title": "Machine Learning Engineer",
        "location": "Pune",
        "score": 0.89,
        "skills": ["Python", "scikit-learn", "SQL"],
        "matched": ["Required skill: Python"],
        "missing": ["Required skill: TensorFlow", "Required skill: PyTorch"],
        "resume_name": "sneha_joshi.pdf",
    },
]


async def seed() -> None:
    settings = get_settings()
    if not settings.database_url:
        raise SystemExit("DATABASE_URL is not set")
    db.init_engine(settings.database_url)
    if db.SessionLocal is None:
        raise SystemExit("Database session is not initialized")
    async with db.SessionLocal() as session:
        job = await session.get(Job, JOB_ID)
        if job is None:
            session.add(
                Job(
                    id=JOB_ID,
                    job_title="AI/ML Engineer",
                    experience_min=3,
                    location="Hyderabad",
                    work_mode="Hybrid",
                    employment_type="Full-time",
                    must_have_skills=["Python", "TensorFlow", "PyTorch"],
                    preferred_skills=["Kubernetes"],
                    education=["M.Tech"],
                    responsibilities=["Train ranking models"],
                    keywords=["Python", "ML"],
                    raw_job_description=(
                        "AI/ML Engineer in Hyderabad. Hybrid. Python, TensorFlow."
                    ),
                )
            )
        for item in DEMO:
            candidate = await session.get(Candidate, item["id"])
            if candidate is None:
                candidate = Candidate(
                    id=item["id"],
                    full_name=item["full_name"],
                    email=item["email"],
                    email_normalized=item["email"],
                    current_job_title=item["current_job_title"],
                    location=item["location"],
                    technical_skills=item["skills"],
                    skills=item["skills"],
                    education=[],
                    certifications=[],
                    companies=[],
                    previous_roles=[],
                    projects=[],
                    achievements=[],
                    industries=[],
                    soft_skills=[],
                    open_to_work_status=OpenToWorkStatus.OPEN_TO_WORK.value,
                    open_to_work_source="candidate_declaration",
                    open_to_work_verified_at=VERIFIED_AT,
                )
                session.add(candidate)
                await session.flush()
            else:
                candidate.open_to_work_status = OpenToWorkStatus.OPEN_TO_WORK.value
                candidate.open_to_work_source = "candidate_declaration"
                candidate.open_to_work_verified_at = VERIFIED_AT
            resume_rows = await session.execute(
                select(CandidateResume).where(CandidateResume.candidate_id == item["id"])
            )
            if resume_rows.scalars().first() is None:
                session.add(
                    CandidateResume(
                        candidate_id=item["id"],
                        file_name=item["resume_name"],
                        source="upload",
                    )
                )
            existing = await session.execute(
                select(JobCandidate).where(
                    JobCandidate.job_id == JOB_ID,
                    JobCandidate.candidate_id == item["id"],
                )
            )
            row = existing.scalar_one_or_none()
            if row is None:
                session.add(
                    JobCandidate(
                        job_id=JOB_ID,
                        candidate_id=item["id"],
                        overall_score=item["score"],
                        matched_requirements=item["matched"],
                        missing_requirements=item["missing"],
                        explanation=(
                            f"Overall match score is {int(item['score'] * 100)}% from "
                            "deterministic requirement scoring plus a separate semantic "
                            "similarity signal. This is not a hiring decision."
                        ),
                        confidence=0.9,
                        review_status=REVIEW_PENDING,
                        workflow_status="PENDING_REVIEW",
                    )
                )
            else:
                row.overall_score = item["score"]
                row.matched_requirements = item["matched"]
                row.missing_requirements = item["missing"]
                row.explanation = (
                    f"Overall match score is {int(item['score'] * 100)}% from "
                    "deterministic requirement scoring plus a separate semantic "
                    "similarity signal. This is not a hiring decision."
                )
                row.review_status = REVIEW_PENDING
                row.workflow_status = "PENDING_REVIEW"
        await session.commit()
    print(f"Seeded AI/ML Engineer job {JOB_ID}")


if __name__ == "__main__":
    asyncio.run(seed())
