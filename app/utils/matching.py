"""Deterministic CandidateProfile vs JobProfile scoring helpers."""

from __future__ import annotations

import math
import re
from difflib import SequenceMatcher

from app.models.candidate import CandidateProfile
from app.models.job import JobProfile, WorkMode
from app.utils.skills import canonicalize_skill

MISSING_SIGNAL = 0.5
TOKEN_RE = re.compile(r"[a-z0-9.+#]+")

TITLE_STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "of",
    "in",
    "for",
    "to",
    "sr",
    "senior",
    "jr",
    "junior",
}


def clamp(value: float) -> float:
    return max(0.0, min(1.0, round(value, 4)))


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return MISSING_SIGNAL
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    norm_left = math.sqrt(sum(a * a for a in left))
    norm_right = math.sqrt(sum(b * b for b in right))
    if norm_left == 0 or norm_right == 0:
        return MISSING_SIGNAL
    return clamp(dot / (norm_left * norm_right))


def canonical_skill_set(names: list[str]) -> set[str]:
    values: set[str] = set()
    for name in names:
        canonical = canonicalize_skill(name).strip().lower()
        if canonical:
            values.add(canonical)
    return values


def skill_covers(required: str, candidate_skills: set[str]) -> bool:
    key = canonicalize_skill(required).strip().lower()
    if not key:
        return False
    return any(key == item or key in item or item in key for item in candidate_skills)


def candidate_skill_pool(candidate: CandidateProfile) -> set[str]:
    names = [
        *candidate.skills,
        *candidate.technical_skills,
        *[tech for project in candidate.projects for tech in project.technologies],
    ]
    return canonical_skill_set(names)


def score_required_skills(
    job: JobProfile, candidate: CandidateProfile
) -> tuple[float, list[str], list[str]]:
    pool = candidate_skill_pool(candidate)
    if not job.must_have_skills:
        return 1.0, [], []
    matched: list[str] = []
    missing: list[str] = []
    for skill in job.must_have_skills:
        if skill_covers(skill, pool):
            matched.append(f"Required skill: {canonicalize_skill(skill)}")
        else:
            missing.append(f"Required skill: {canonicalize_skill(skill)}")
    return clamp(len(matched) / len(job.must_have_skills)), matched, missing


def score_preferred_skills(
    job: JobProfile, candidate: CandidateProfile
) -> tuple[float, list[str]]:
    pool = candidate_skill_pool(candidate)
    if not job.preferred_skills:
        return 1.0, []
    matched: list[str] = []
    for skill in job.preferred_skills:
        if skill_covers(skill, pool):
            matched.append(f"Preferred skill: {canonicalize_skill(skill)}")
    return clamp(len(matched) / len(job.preferred_skills)), matched


def score_experience(
    job: JobProfile, candidate: CandidateProfile
) -> tuple[float, list[str], list[str]]:
    if job.experience_min is None and job.experience_max is None:
        return 1.0, [], []
    years = candidate.total_experience_years
    if years is None:
        return MISSING_SIGNAL, [], []
    matched: list[str] = []
    missing: list[str] = []
    score = 1.0
    if job.experience_min is not None:
        if years >= job.experience_min:
            matched.append(
                f"Experience: {years:g} years meets minimum {job.experience_min:g}"
            )
        else:
            score = years / job.experience_min if job.experience_min else 0.0
            missing.append(
                f"Experience: minimum {job.experience_min:g} years "
                f"(candidate has {years:g})"
            )
    if job.experience_max is not None and years > job.experience_max:
        over = years - job.experience_max
        score = min(score, clamp(1.0 - min(over, job.experience_max) / (job.experience_max * 4 + 1)))
    return clamp(score), matched, missing


def _tokens(value: str | None) -> set[str]:
    if not value:
        return set()
    return {token for token in TOKEN_RE.findall(value.lower()) if token}


def score_title(job: JobProfile, candidate: CandidateProfile) -> float:
    job_title = job.job_title
    titles = [
        candidate.current_job_title,
        *[role.title for role in candidate.previous_roles],
    ]
    titles = [title for title in titles if title]
    if not job_title or not titles:
        return MISSING_SIGNAL
    best = 0.0
    job_tokens = _tokens(job_title) - TITLE_STOPWORDS
    for title in titles:
        ratio = SequenceMatcher(None, job_title.lower(), title.lower()).ratio()
        cand_tokens = _tokens(title) - TITLE_STOPWORDS
        if job_tokens and cand_tokens:
            overlap = len(job_tokens & cand_tokens) / len(job_tokens | cand_tokens)
        else:
            overlap = 0.0
        best = max(best, 0.5 * ratio + 0.5 * overlap)
    return clamp(best)


def _education_blob(candidate: CandidateProfile) -> str:
    parts: list[str] = []
    for item in candidate.education:
        parts.extend(
            [item.institution or "", item.degree or "", item.field or ""]
        )
    return " ".join(part for part in parts if part)


def score_education(
    job: JobProfile, candidate: CandidateProfile
) -> tuple[float, list[str], list[str]]:
    if not job.education:
        return 1.0, [], []
    blob = _education_blob(candidate)
    if not blob:
        return MISSING_SIGNAL, [], []
    blob_tokens = _tokens(blob)
    matched: list[str] = []
    missing: list[str] = []
    hits = 0
    for requirement in job.education:
        req_tokens = {token for token in _tokens(requirement) if len(token) > 2}
        if req_tokens and req_tokens & blob_tokens:
            hits += 1
            matched.append(f"Education: {requirement}")
        else:
            missing.append(f"Education: {requirement}")
    if not job.education:
        return 1.0, matched, missing
    return clamp(hits / len(job.education)), matched, missing


def score_projects(job: JobProfile, candidate: CandidateProfile) -> float:
    targets = canonical_skill_set(
        [*job.must_have_skills, *job.preferred_skills, *job.keywords]
    )
    if not targets:
        return 1.0
    if not candidate.projects:
        return MISSING_SIGNAL
    project_terms: set[str] = set()
    for project in candidate.projects:
        project_terms |= canonical_skill_set(project.technologies)
        project_terms |= _tokens(project.name)
        project_terms |= _tokens(project.description)
    if not project_terms:
        return MISSING_SIGNAL
    hits = sum(1 for term in targets if skill_covers(term, project_terms))
    return clamp(hits / len(targets)) if targets else 1.0


def score_location(job: JobProfile, candidate: CandidateProfile) -> float:
    if job.work_mode is WorkMode.REMOTE:
        return 1.0
    if not job.location or not candidate.location:
        if job.work_mode in {WorkMode.FLEXIBLE, WorkMode.HYBRID}:
            return 0.7
        return MISSING_SIGNAL
    job_loc = job.location.strip().lower()
    cand_loc = candidate.location.strip().lower()
    if job_loc in cand_loc or cand_loc in job_loc:
        return 1.0
    job_tokens = {token for token in _tokens(job.location) if len(token) > 3}
    cand_tokens = {token for token in _tokens(candidate.location) if len(token) > 3}
    if job_tokens and job_tokens & cand_tokens:
        return 0.9
    if job.work_mode is WorkMode.HYBRID:
        return 0.55
    if job.work_mode is WorkMode.FLEXIBLE:
        return 0.65
    return 0.35


def score_availability(candidate: CandidateProfile) -> float:
    text = " ".join(
        part
        for part in (candidate.availability, candidate.notice_period)
        if part
    ).lower()
    if not text:
        return MISSING_SIGNAL
    if any(token in text for token in ("immediate", "immediately", "available now")):
        return 1.0
    match = re.search(r"(\d+)\s*day", text)
    if match:
        days = int(match.group(1))
        if days <= 15:
            return 0.95
        if days <= 30:
            return 0.85
        if days <= 60:
            return 0.7
        return 0.6
    if "available" in text or "notice" in text:
        return 0.8
    return 0.7


def job_embedding_text(job: JobProfile) -> str:
    parts = [
        job.job_title or "",
        job.location or "",
        job.work_mode.value if job.work_mode else "",
        " ".join(job.must_have_skills),
        " ".join(job.preferred_skills),
        " ".join(job.responsibilities),
        " ".join(job.keywords),
        " ".join(job.education),
    ]
    return " ".join(part for part in parts if part).strip()


def candidate_embedding_text(candidate: CandidateProfile) -> str:
    """Role/skills text only. Name, contact, and protected fields are omitted."""
    titles = [
        candidate.current_job_title or "",
        *[role.title or "" for role in candidate.previous_roles],
    ]
    project_bits = [
        f"{project.name or ''} {' '.join(project.technologies)} {project.description or ''}"
        for project in candidate.projects
    ]
    parts = [
        " ".join(title for title in titles if title),
        " ".join(candidate.skills),
        " ".join(candidate.technical_skills),
        candidate.resume_summary or "",
        " ".join(project_bits),
        _education_blob(candidate),
        candidate.location or "",
    ]
    return " ".join(part for part in parts if part).strip()
