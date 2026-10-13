"""Rank MatchResult rows for one job. No outreach and no new scoring criteria."""

from __future__ import annotations

import logging
from uuid import UUID

from app.models.match import MatchResult
from app.models.ranking import RankedCandidate
from app.utils.matching import MISSING_SIGNAL, clamp

logger = logging.getLogger(__name__)

# Same component scores the Matching Agent already produces. Availability is
# already folded into MatchResult.overall_score, so default ranking uses that.
COMPONENT_SCORES = (
    "required_skill_score",
    "preferred_skill_score",
    "experience_score",
    "title_similarity_score",
    "education_score",
    "project_score",
    "location_score",
    "semantic_score",
)


class RankingEngine:
    """Order a job's MatchResult list. Missing scores are treated as incomplete, not a reject."""

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self.weights = self._validated_weights(weights)

    def generate_shortlist(
        self,
        job_id: UUID,
        matches: list[MatchResult],
        *,
        min_score: float | None = None,
        top_n: int | None = None,
    ) -> list[RankedCandidate]:
        ordered = self.sort_by_score(matches)
        if min_score is not None:
            ordered = self.apply_minimum_threshold(ordered, min_score)
        if top_n is not None:
            ordered = self.get_top_candidates(ordered, top_n)
        shortlist = [
            self._to_ranked(job_id, match, rank)
            for rank, match in enumerate(ordered, start=1)
        ]
        logger.info(
            "RankingEngine.generate_shortlist completed",
            extra={
                "job_id": str(job_id),
                "input_count": len(matches),
                "shortlist_count": len(shortlist),
            },
        )
        return shortlist

    def sort_by_score(self, matches: list[MatchResult]) -> list[MatchResult]:
        return sorted(matches, key=self._sort_key)

    def apply_minimum_threshold(
        self, matches: list[MatchResult], threshold: float
    ) -> list[MatchResult]:
        return [
            match
            for match in matches
            if self._effective_score(match) >= threshold
        ]

    def get_top_candidates(
        self, matches: list[MatchResult], n: int
    ) -> list[MatchResult]:
        if n <= 0:
            return []
        ordered = self.sort_by_score(matches)
        return ordered[:n]

    def _effective_score(self, match: MatchResult) -> float:
        if not self.weights:
            overall = getattr(match, "overall_score", None)
            if overall is None:
                return MISSING_SIGNAL
            return clamp(float(overall))
        weighted = 0.0
        total = 0.0
        for field, weight in self.weights.items():
            value = getattr(match, field, None)
            if value is None:
                value = MISSING_SIGNAL
            weighted += float(value) * weight
            total += weight
        if total <= 0:
            return MISSING_SIGNAL
        return clamp(weighted / total)

    def _sort_key(self, match: MatchResult) -> tuple:
        candidate_key = (
            str(match.candidate_id) if match.candidate_id is not None else ""
        )
        generated = getattr(match, "generated_at", None)
        generated_key = generated.isoformat() if generated is not None else ""
        return (-self._effective_score(match), candidate_key, generated_key)

    def _to_ranked(
        self, job_id: UUID, match: MatchResult, rank: int
    ) -> RankedCandidate:
        return RankedCandidate(
            rank=rank,
            candidate_id=match.candidate_id,
            job_id=job_id,
            overall_score=self._effective_score(match),
            matched_requirements=list(match.matched_requirements),
            missing_requirements=list(match.missing_requirements),
            explanation=match.explanation,
            confidence=match.confidence,
        )

    @staticmethod
    def _validated_weights(
        weights: dict[str, float] | None,
    ) -> dict[str, float] | None:
        if not weights:
            return None
        cleaned: dict[str, float] = {}
        for field, weight in weights.items():
            if field not in COMPONENT_SCORES:
                continue
            if weight < 0:
                continue
            cleaned[field] = float(weight)
        return cleaned or None
