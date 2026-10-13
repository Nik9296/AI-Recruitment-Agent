"""Deterministic resume-text helpers used after structured LLM extraction."""

from __future__ import annotations

import re

YEARS_EXPERIENCE_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:experience|exp)\b",
    re.IGNORECASE,
)
EXPERIENCE_LABEL_RE = re.compile(
    r"(?:total\s+)?(?:experience|exp)\s*[:\-]\s*(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)?",
    re.IGNORECASE,
)
NOTICE_RE = re.compile(r"notice\s*period", re.IGNORECASE)
AVAILABILITY_RE = re.compile(
    r"\b(availability|available|immediate joining|serving notice)\b",
    re.IGNORECASE,
)
WORK_AUTH_RE = re.compile(
    r"\b(work authorization|work permit|employment authorization|"
    r"authorized to work|citizen|citizenship|visa|h-?1b|opt|green card)\b",
    re.IGNORECASE,
)


def parse_stated_experience_years(text: str) -> float | None:
    """Return years only from an explicit experience statement. Never guess."""
    if not text or not text.strip():
        return None
    match = YEARS_EXPERIENCE_RE.search(text) or EXPERIENCE_LABEL_RE.search(text)
    if not match:
        return None
    return float(match.group(1))


def experience_is_supported(years: float | None, text: str) -> bool:
    if years is None:
        return False
    stated = parse_stated_experience_years(text)
    if stated is None:
        return False
    return abs(stated - float(years)) < 0.51


def value_supported_by_text(value: str | None, text: str) -> bool:
    if not value or not text:
        return False
    haystack = text.lower()
    needle = value.strip().lower()
    if needle and needle in haystack:
        return True
    tokens = [token for token in re.split(r"[^a-z0-9]+", needle) if len(token) > 2]
    return bool(tokens) and all(token in haystack for token in tokens)


def notice_period_is_stated(text: str) -> bool:
    return bool(NOTICE_RE.search(text or ""))


def availability_is_stated(text: str) -> bool:
    return bool(AVAILABILITY_RE.search(text or ""))


def work_authorization_is_stated(text: str) -> bool:
    return bool(WORK_AUTH_RE.search(text or ""))


def phone_supported_by_text(phone: str | None, text: str) -> bool:
    if not phone or not text:
        return False
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 7:
        return False
    haystack = re.sub(r"\D", "", text)
    return digits in haystack
