"""LLM extraction and repair for job descriptions."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.jd_agent.prompts import EXTRACTION_SYSTEM, REPAIR_SYSTEM
from app.core.llm import get_chat_model
from app.models.job_description import RawJobExtraction

ExtractorFn = Callable[[str], Awaitable[dict[str, Any]]]
RepairFn = Callable[[str, dict[str, Any], list[str]], Awaitable[dict[str, Any]]]


def _to_dict(result: Any) -> dict[str, Any]:
    if result is None:
        return {}
    if hasattr(result, "model_dump"):
        return result.model_dump()
    if isinstance(result, dict):
        return result
    return {}


async def extract_raw_job(raw_jd: str) -> dict[str, Any]:
    llm = get_chat_model().with_structured_output(RawJobExtraction)
    result = await llm.ainvoke(
        [
            SystemMessage(content=EXTRACTION_SYSTEM),
            HumanMessage(content=f"Job description:\n\n{raw_jd}"),
        ]
    )
    return _to_dict(result)


async def repair_raw_job(
    raw_jd: str, previous: dict[str, Any], errors: list[str]
) -> dict[str, Any]:
    llm = get_chat_model().with_structured_output(RawJobExtraction)
    result = await llm.ainvoke(
        [
            SystemMessage(content=REPAIR_SYSTEM),
            HumanMessage(
                content=(
                    "Original job description:\n"
                    f"{raw_jd}\n\n"
                    "Previous extraction JSON:\n"
                    f"{json.dumps(previous, default=str)}\n\n"
                    "Validation errors:\n"
                    + "\n".join(f"- {error}" for error in errors)
                )
            ),
        ]
    )
    return _to_dict(result)
