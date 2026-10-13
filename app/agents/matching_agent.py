"""Matching Agent: hybrid deterministic + semantic Candidate vs Job scoring."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from app.models.candidate import CandidateProfile
from app.models.job import JobProfile
from app.models.match import MatchResult
from app.services.embeddings import Embedder, get_embedding_model
from app.services.llm import LLMConfigurationError
from app.utils.matching import (
    MISSING_SIGNAL,
    candidate_embedding_text,
    clamp,
    cosine_similarity,
    job_embedding_text,
    score_availability,
    score_education,
    score_experience,
    score_location,
    score_preferred_skills,
    score_projects,
    score_required_skills,
    score_title,
)

logger = logging.getLogger(__name__)

# Deterministic requirements dominate. Semantic similarity is a separate signal.
SCORE_WEIGHTS = {
    "required_skill_score": 0.28,
    "preferred_skill_score": 0.10,
    "experience_score": 0.14,
    "title_similarity_score": 0.10,
    "education_score": 0.08,
    "project_score": 0.08,
    "location_score": 0.07,
    "availability_score": 0.05,
    "semantic_score": 0.10,
}


class MatchingAgentError(Exception):
    """Base error for matching failures."""


class MatchingAgent:
    """Compare a candidate to a job. The LLM does not decide the final score."""

    def __init__(self, embedder: Embedder | None = None) -> None:
        self._embedder = embedder

    def match(
        self,
        candidate: CandidateProfile,
        job: JobProfile,
        *,
        job_id: UUID | None = None,
        candidate_id: UUID | None = None,
    ) -> MatchResult:
        required_score, required_matched, required_missing = score_required_skills(
            job, candidate
        )
        preferred_score, preferred_matched = score_preferred_skills(job, candidate)
        experience_score, experience_matched, experience_missing = score_experience(
            job, candidate
        )
        title_score = score_title(job, candidate)
        education_score, education_matched, education_missing = score_education(
            job, candidate
        )
        project_score = score_projects(job, candidate)
        location_score = score_location(job, candidate)
        availability_score = score_availability(candidate)
        semantic_score, semantic_used = self._semantic_score(candidate, job)

        overall = clamp(
            required_score * SCORE_WEIGHTS["required_skill_score"]
            + preferred_score * SCORE_WEIGHTS["preferred_skill_score"]
            + experience_score * SCORE_WEIGHTS["experience_score"]
            + title_score * SCORE_WEIGHTS["title_similarity_score"]
            + education_score * SCORE_WEIGHTS["education_score"]
            + project_score * SCORE_WEIGHTS["project_score"]
            + location_score * SCORE_WEIGHTS["location_score"]
            + availability_score * SCORE_WEIGHTS["availability_score"]
            + semantic_score * SCORE_WEIGHTS["semantic_score"]
        )

        matched = [
            *required_matched,
            *preferred_matched,
            *experience_matched,
            *education_matched,
        ]
        if availability_score >= 0.85 and (
            candidate.availability or candidate.notice_period
        ):
            matched.append(
                "Availability: "
                + (candidate.availability or candidate.notice_period or "")
            )

        missing = [*required_missing, *experience_missing, *education_missing]
        confidence = self._confidence(
            job,
            candidate,
            semantic_used=semantic_used,
        )
        explanation = self._explain(
            overall=overall,
            required_score=required_score,
            missing=missing,
            matched=matched,
            experience_score=experience_score,
            location_score=location_score,
            semantic_score=semantic_score,
            semantic_used=semantic_used,
        )
        logger.info(
            "MatchingAgent.match completed",
            extra={
                "overall_score": overall,
                "required_skill_score": required_score,
                "semantic_score": semantic_score,
                "missing_requirement_count": len(missing),
                "has_candidate_id": (candidate_id or candidate.candidate_id) is not None,
            },
        )
        return MatchResult(
            candidate_id=candidate_id or candidate.candidate_id,
            job_id=job_id,
            overall_score=overall,
            required_skill_score=required_score,
            preferred_skill_score=preferred_score,
            experience_score=experience_score,
            title_similarity_score=title_score,
            education_score=education_score,
            project_score=project_score,
            location_score=location_score,
            semantic_score=semantic_score,
            matched_requirements=matched,
            missing_requirements=missing,
            explanation=explanation,
            confidence=confidence,
            generated_at=datetime.now(UTC),
        )

    def _semantic_score(
        self, candidate: CandidateProfile, job: JobProfile
    ) -> tuple[float, bool]:
        job_text = job_embedding_text(job)
        candidate_text = candidate_embedding_text(candidate)
        if not job_text or not candidate_text:
            return MISSING_SIGNAL, False
        try:
            embedder = self._embedder or get_embedding_model()
            vectors = embedder.embed_documents([job_text, candidate_text])
        except (LLMConfigurationError, NotImplementedError, Exception):
            logger.warning("MatchingAgent semantic embeddings unavailable")
            return MISSING_SIGNAL, False
        if len(vectors) < 2:
            return MISSING_SIGNAL, False
        return cosine_similarity(vectors[0], vectors[1]), True

    @staticmethod
    def _confidence(
        job: JobProfile,
        candidate: CandidateProfile,
        *,
        semantic_used: bool,
    ) -> float:
        signals = [
            bool(job.must_have_skills),
            bool(candidate.skills or candidate.technical_skills),
            job.experience_min is not None or job.experience_max is not None,
            candidate.total_experience_years is not None,
            bool(job.job_title),
            bool(candidate.current_job_title or candidate.previous_roles),
            bool(job.education),
            bool(candidate.education),
            bool(job.location or job.work_mode),
            bool(candidate.location),
            semantic_used,
        ]
        filled = sum(1 for item in signals if item)
        return clamp(0.35 + 0.65 * (filled / len(signals)))

    @staticmethod
    def _explain(
        *,
        overall: float,
        required_score: float,
        missing: list[str],
        matched: list[str],
        experience_score: float,
        location_score: float,
        semantic_score: float,
        semantic_used: bool,
    ) -> str:
        parts = [
            f"Overall match score is {overall:.0%} from deterministic requirement "
            f"scoring plus a separate semantic similarity signal "
            f"({semantic_score:.0%}"
            + (" used" if semantic_used else " unused; treated as neutral")
            + ").",
            f"Required-skill coverage is {required_score:.0%}.",
        ]
        if matched:
            parts.append("Matched: " + "; ".join(matched[:8]) + ".")
        if missing:
            parts.append(
                "Gaps (not an automatic rejection): " + "; ".join(missing[:8]) + "."
            )
        else:
            parts.append("No explicit requirement gaps were recorded.")
        parts.append(
            f"Experience score {experience_score:.0%}; "
            f"location/work-mode score {location_score:.0%}. "
            "Missing fields were scored as incomplete signals, not as a reject. "
            "This is not a hiring decision."
        )
        return " ".join(parts)
