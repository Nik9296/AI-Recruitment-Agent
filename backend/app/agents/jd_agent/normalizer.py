"""Deterministic JD normalization. No LLM calls."""

from __future__ import annotations

import re
from typing import Any

from app.agents.jd_agent.skills_taxonomy import canonicalize_skill
from app.models.enums import EducationLevel, EmploymentType, WorkMode

SENIORITY_RANGES: dict[str, tuple[float, float]] = {
    "intern": (0.0, 1.0),
    "internship": (0.0, 1.0),
    "fresher": (0.0, 1.0),
    "graduate": (0.0, 1.0),
    "entry-level": (0.0, 2.0),
    "entry level": (0.0, 2.0),
    "junior": (0.0, 2.0),
    "mid": (2.0, 5.0),
    "mid-level": (2.0, 5.0),
    "mid level": (2.0, 5.0),
    "senior": (5.0, 8.0),
    "staff": (7.0, 12.0),
    "principal": (10.0, 15.0),
    "lead": (6.0, 10.0),
}

WORK_MODE_ALIASES: dict[str, WorkMode] = {
    "remote": WorkMode.REMOTE,
    "wfh": WorkMode.REMOTE,
    "w.f.h": WorkMode.REMOTE,
    "work from home": WorkMode.REMOTE,
    "work-from-home": WorkMode.REMOTE,
    "fully remote": WorkMode.REMOTE,
    "hybrid": WorkMode.HYBRID,
    "onsite": WorkMode.ONSITE,
    "on-site": WorkMode.ONSITE,
    "on site": WorkMode.ONSITE,
    "in-office": WorkMode.ONSITE,
    "in office": WorkMode.ONSITE,
    "office": WorkMode.ONSITE,
    "unknown": WorkMode.UNKNOWN,
}

EMPLOYMENT_ALIASES: dict[str, EmploymentType] = {
    "full time": EmploymentType.FULL_TIME,
    "full-time": EmploymentType.FULL_TIME,
    "fulltime": EmploymentType.FULL_TIME,
    "full_time": EmploymentType.FULL_TIME,
    "fte": EmploymentType.FULL_TIME,
    "permanent": EmploymentType.FULL_TIME,
    "part time": EmploymentType.PART_TIME,
    "part-time": EmploymentType.PART_TIME,
    "parttime": EmploymentType.PART_TIME,
    "part_time": EmploymentType.PART_TIME,
    "contract": EmploymentType.CONTRACT,
    "contractor": EmploymentType.CONTRACT,
    "freelance": EmploymentType.CONTRACT,
    "consultant": EmploymentType.CONTRACT,
    "intern": EmploymentType.INTERNSHIP,
    "internship": EmploymentType.INTERNSHIP,
    "temporary": EmploymentType.TEMPORARY,
    "temp": EmploymentType.TEMPORARY,
    "unknown": EmploymentType.UNKNOWN,
}

EDUCATION_ALIASES: dict[str, EducationLevel] = {
    "high school": EducationLevel.HIGH_SCHOOL,
    "high_school": EducationLevel.HIGH_SCHOOL,
    "secondary": EducationLevel.HIGH_SCHOOL,
    "associate": EducationLevel.ASSOCIATE,
    "associates": EducationLevel.ASSOCIATE,
    "bachelor": EducationLevel.BACHELORS,
    "bachelors": EducationLevel.BACHELORS,
    "bachelor's": EducationLevel.BACHELORS,
    "undergraduate": EducationLevel.BACHELORS,
    "bs": EducationLevel.BACHELORS,
    "ba": EducationLevel.BACHELORS,
    "b.tech": EducationLevel.BACHELORS,
    "btech": EducationLevel.BACHELORS,
    "be": EducationLevel.BACHELORS,
    "master": EducationLevel.MASTERS,
    "masters": EducationLevel.MASTERS,
    "master's": EducationLevel.MASTERS,
    "ms": EducationLevel.MASTERS,
    "m.tech": EducationLevel.MASTERS,
    "mba": EducationLevel.MASTERS,
    "phd": EducationLevel.PHD,
    "ph.d": EducationLevel.PHD,
    "doctorate": EducationLevel.PHD,
    "none_specified": EducationLevel.NONE_SPECIFIED,
    "none": EducationLevel.NONE_SPECIFIED,
    "unspecified": EducationLevel.NONE_SPECIFIED,
}

TITLE_ACRONYMS = {
    "ai",
    "ml",
    "sre",
    "swe",
    "qa",
    "hr",
    "it",
    "ios",
    "api",
    "aws",
    "gcp",
    "sql",
    "ui",
    "ux",
    "cto",
    "vp",
}

RANGE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:[-–—]|to)\s*(\d+(?:\.\d+)?)", re.IGNORECASE)
PLUS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*\+", re.IGNORECASE)
SINGLE_YEARS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?)", re.IGNORECASE)
REMOTE_LOCATION_RE = re.compile(
    r"\b(remote|anywhere|work from home|wfh)\b", re.IGNORECASE
)


def _norm_key(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.strip().lower().replace("_", " ").split())


def map_work_mode(value: Any) -> WorkMode:
    if isinstance(value, WorkMode):
        return value
    key = _norm_key(str(value) if value is not None else "")
    return WORK_MODE_ALIASES.get(key, WorkMode.UNKNOWN)


def map_employment_type(value: Any) -> EmploymentType:
    if isinstance(value, EmploymentType):
        return value
    key = _norm_key(str(value) if value is not None else "")
    return EMPLOYMENT_ALIASES.get(key, EmploymentType.UNKNOWN)


def map_education_level(value: Any) -> EducationLevel:
    if isinstance(value, EducationLevel):
        return value
    if value is None or value == "":
        return EducationLevel.NONE_SPECIFIED
    key = _norm_key(str(value))
    if key in EDUCATION_ALIASES:
        return EDUCATION_ALIASES[key]
    for alias, level in EDUCATION_ALIASES.items():
        if alias in key:
            return level
    return EducationLevel.NONE_SPECIFIED


def normalize_title(title: str | None) -> str:
    text = (title or "").strip()
    if not text:
        return text
    letters = [char for char in text if char.isalpha()]
    uppercase = sum(1 for char in letters if char.isupper())
    has_lower = any(char.islower() for char in letters)
    if letters and uppercase >= 2 and has_lower:
        return text
    words: list[str] = []
    for word in text.split():
        lowered = re.sub(r"[^a-z0-9]+", "", word.lower())
        if lowered in TITLE_ACRONYMS:
            core = re.sub(r"[^A-Za-z0-9+.#]", "", word)
            words.append(word.replace(core, core.upper()) if core else word.upper())
        elif word.isupper() and 2 <= len(lowered) <= 4:
            words.append(word)
        else:
            words.append(word.capitalize())
    return " ".join(words)


def parse_experience(
    raw: str | None,
    min_years: float | None,
    max_years: float | None,
    notes: list[str],
) -> tuple[float | None, float | None]:
    if min_years is not None and max_years is not None:
        return min_years, max_years

    text = raw or ""
    match = RANGE_RE.search(text)
    if match:
        low, high = float(match.group(1)), float(match.group(2))
        return (
            min_years if min_years is not None else low,
            max_years if max_years is not None else high,
        )

    plus = PLUS_RE.search(text)
    if plus:
        return min_years if min_years is not None else float(plus.group(1)), max_years

    single = SINGLE_YEARS_RE.search(text)
    if single and min_years is None:
        min_years = float(single.group(1))

    lowered = text.lower()
    if min_years is None and max_years is None:
        for term, (low, high) in SENIORITY_RANGES.items():
            if re.search(rf"\b{re.escape(term)}\b", lowered):
                notes.append(f"Experience inferred from seniority term '{term}'")
                return low, high

    return min_years, max_years


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, dict):
        return value
    return {}


def _normalize_skill_list(values: Any) -> list[str]:
    if not values:
        return []
    if not isinstance(values, list):
        values = [values]
    seen: set[str] = set()
    out: list[str] = []
    for item in values:
        canonical = canonicalize_skill(str(item))
        if not canonical:
            continue
        key = canonical.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(canonical)
    return out


def normalize_extraction(raw: dict[str, Any] | None) -> dict[str, Any]:
    payload = dict(raw or {})
    notes = [
        str(note).strip()
        for note in (payload.get("extraction_notes") or [])
        if str(note).strip()
    ]

    experience = _as_dict(payload.get("experience"))
    min_years = experience.get("min_years")
    max_years = experience.get("max_years")
    exp_raw = experience.get("raw")
    min_years, max_years = parse_experience(exp_raw, min_years, max_years, notes)

    location = _as_dict(payload.get("location"))
    work_mode = map_work_mode(payload.get("work_mode"))
    loc_raw = location.get("raw")
    is_remote = bool(location.get("is_remote"))
    if work_mode is WorkMode.REMOTE or (loc_raw and REMOTE_LOCATION_RE.search(str(loc_raw))):
        is_remote = True
        if work_mode is WorkMode.UNKNOWN and loc_raw and REMOTE_LOCATION_RE.search(str(loc_raw)):
            work_mode = WorkMode.REMOTE

    must_have = _normalize_skill_list(payload.get("must_have_skills"))
    preferred = _normalize_skill_list(payload.get("preferred_skills"))
    must_keys = {skill.lower() for skill in must_have}
    preferred = [skill for skill in preferred if skill.lower() not in must_keys]

    keyword_source: list[str] = []
    keyword_source.extend(must_have)
    keyword_source.extend(preferred)
    keyword_source.extend(payload.get("keywords") or [])
    keywords: list[str] = []
    seen_kw: set[str] = set()
    for item in keyword_source:
        key = str(item).strip().lower()
        if not key or key in seen_kw:
            continue
        seen_kw.add(key)
        keywords.append(key)

    education = payload.get("education") or []
    if not isinstance(education, list):
        education = [education]

    return {
        "title": normalize_title(payload.get("title")),
        "experience": {
            "min_years": min_years,
            "max_years": max_years,
            "raw": exp_raw,
        },
        "location": {
            "raw": loc_raw,
            "city": location.get("city"),
            "state": location.get("state"),
            "country": location.get("country"),
            "is_remote": is_remote,
        },
        "work_mode": work_mode,
        "employment_type": map_employment_type(payload.get("employment_type")),
        "must_have_skills": must_have,
        "preferred_skills": preferred,
        "education": [str(item).strip() for item in education if str(item).strip()],
        "education_level": map_education_level(payload.get("education_level")),
        "responsibilities": payload.get("responsibilities") or [],
        "keywords": keywords,
        "confidence": payload.get("confidence"),
        "extraction_notes": notes,
    }
