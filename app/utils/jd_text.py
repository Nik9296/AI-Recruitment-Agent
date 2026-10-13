"""Deterministic JD text helpers used after structured LLM extraction."""

from __future__ import annotations

import re

from app.models.job import EmploymentType, WorkMode

RANGE_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:[-–—]|to)\s*(\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:years?|yrs?)",
    re.IGNORECASE,
)
PLUS_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*\+\s*(?:years?|yrs?)",
    re.IGNORECASE,
)
MINIMUM_RE = re.compile(
    r"(?:minimum|at least|min(?:imum)?)\s+(\d+(?:\.\d+)?)\s*(?:years?|yrs?)",
    re.IGNORECASE,
)
SINGLE_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\s+(?:of\s+)?(?:experience|exp\b)",
    re.IGNORECASE,
)
FRESHER_RE = re.compile(
    r"\b(freshers?|no experience|entry[- ]level|graduate trainee)\b",
    re.IGNORECASE,
)
INTERN_RE = re.compile(r"\b(intern|internship)\b", re.IGNORECASE)
WORK_MODE_WORDS = {"remote", "hybrid", "onsite", "on-site", "wfh", "flexible"}
NON_LOCATIONS = WORK_MODE_WORDS | {
    "anywhere",
    "worldwide",
    "global",
    "n/a",
    "na",
    "unspecified",
}
KNOWN_CITIES = (
    "bengaluru",
    "bangalore",
    "hyderabad",
    "gurgaon",
    "gurugram",
    "chennai",
    "kolkata",
    "mumbai",
    "jaipur",
    "noida",
    "delhi",
    "pune",
)


def infer_location(text: str) -> str | None:
    lowered = text.lower()
    for city in KNOWN_CITIES:
        match = re.search(rf"\b{re.escape(city)}\b", lowered)
        if match:
            return text[match.start() : match.end()]
    return None


def parse_experience(text: str) -> tuple[float | None, float | None]:
    match = RANGE_RE.search(text)
    if match:
        return float(match.group(1)), float(match.group(2))
    match = PLUS_RE.search(text)
    if match:
        return float(match.group(1)), None
    match = MINIMUM_RE.search(text)
    if match:
        return float(match.group(1)), None
    match = SINGLE_RE.search(text)
    if match:
        return float(match.group(1)), None
    if FRESHER_RE.search(text) or INTERN_RE.search(text):
        return 0.0, 1.0
    return None, None


def infer_work_mode(text: str) -> WorkMode | None:
    lowered = text.lower()
    has_hybrid = bool(re.search(r"\bhybrid\b", lowered))
    has_remote = bool(
        re.search(r"\b(fully remote|work from home|wfh|remote)\b", lowered)
    )
    has_onsite = bool(
        re.search(
            r"\b(on-site|onsite|in-office|in office|work from office|wfo)\b",
            lowered,
        )
    )
    if has_hybrid or (has_remote and has_onsite):
        return WorkMode.HYBRID
    if has_remote:
        return WorkMode.REMOTE
    if has_onsite:
        return WorkMode.ON_SITE
    if re.search(r"\bflexible\b", lowered):
        return WorkMode.FLEXIBLE
    return None


def infer_employment_type(text: str) -> EmploymentType | None:
    lowered = text.lower()
    if INTERN_RE.search(lowered):
        return EmploymentType.INTERNSHIP
    if re.search(r"\bfreelance\b", lowered):
        return EmploymentType.FREELANCE
    if re.search(r"\b(contract|contractor)\b", lowered):
        return EmploymentType.CONTRACT
    if re.search(r"\bpart[ -]?time\b", lowered):
        return EmploymentType.PART_TIME
    if re.search(r"\b(full[ -]?time|permanent|fte)\b", lowered):
        return EmploymentType.FULL_TIME
    return None


def location_is_supported(location: str, job_description: str) -> bool:
    loc = location.strip().lower()
    if loc in NON_LOCATIONS:
        return False
    haystack = job_description.lower()
    if loc in haystack:
        return True
    tokens = [token for token in re.split(r"[^a-z0-9]+", loc) if len(token) > 3]
    return any(token in haystack for token in tokens)
