"""LangGraph state for the JD analysis subgraph."""

from typing import Any, TypedDict

from app.models.job_description import AnalyzedJobDescription


class JDAgentState(TypedDict):
    raw_jd: str
    raw_extraction: dict[str, Any] | None
    analyzed_jd: AnalyzedJobDescription | None
    errors: list[str]
    repair_attempts: int
