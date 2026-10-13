"""JD analysis LangGraph subgraph."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agents.jd_agent.extractor import extract_raw_job, repair_raw_job
from app.agents.jd_agent.normalizer import normalize_extraction
from app.agents.jd_agent.state import JDAgentState
from app.agents.jd_agent.validators import validate_extraction
from app.core.exceptions import JDAnalysisError, LLMConfigurationError
from app.models.job_description import AnalyzedJobDescription

MAX_REPAIR_ATTEMPTS = 1

ExtractorFn = Callable[[str], Awaitable[dict[str, Any]]]
RepairFn = Callable[[str, dict[str, Any], list[str]], Awaitable[dict[str, Any]]]


def _initial_state(raw_jd: str) -> JDAgentState:
    return {
        "raw_jd": raw_jd,
        "raw_extraction": None,
        "analyzed_jd": None,
        "errors": [],
        "repair_attempts": 0,
    }


def compile_jd_graph(
    *,
    extractor: ExtractorFn | None = None,
    repairer: RepairFn | None = None,
) -> CompiledStateGraph:
    extract_fn = extractor or extract_raw_job
    repair_fn = repairer or repair_raw_job

    async def extract_node(state: JDAgentState) -> dict[str, Any]:
        try:
            raw = await extract_fn(state["raw_jd"])
            return {"raw_extraction": raw, "errors": []}
        except LLMConfigurationError:
            raise
        except Exception as exc:  # noqa: BLE001 — surface LLM failures into repair/validate
            return {
                "raw_extraction": state.get("raw_extraction") or {},
                "errors": [f"Extraction failed: {exc}"],
            }

    def normalize_node(state: JDAgentState) -> dict[str, Any]:
        return {"raw_extraction": normalize_extraction(state.get("raw_extraction") or {})}

    def validate_node(state: JDAgentState) -> dict[str, Any]:
        analyzed, errors = validate_extraction(state.get("raw_extraction") or {})
        prior = list(state.get("errors") or [])
        if analyzed is None:
            return {"analyzed_jd": None, "errors": prior + errors}
        return {"analyzed_jd": analyzed, "errors": []}

    async def repair_node(state: JDAgentState) -> dict[str, Any]:
        try:
            repaired = await repair_fn(
                state["raw_jd"],
                state.get("raw_extraction") or {},
                state.get("errors") or [],
            )
            return {
                "raw_extraction": repaired,
                "repair_attempts": int(state.get("repair_attempts") or 0) + 1,
                "errors": [],
            }
        except LLMConfigurationError:
            raise
        except Exception as exc:  # noqa: BLE001
            return {
                "repair_attempts": int(state.get("repair_attempts") or 0) + 1,
                "errors": [f"Repair failed: {exc}"],
            }

    def route_after_validate(
        state: JDAgentState,
    ) -> Literal["ok", "repair", "failed"]:
        if state.get("analyzed_jd") is not None and not state.get("errors"):
            return "ok"
        attempts = int(state.get("repair_attempts") or 0)
        if attempts < MAX_REPAIR_ATTEMPTS:
            return "repair"
        return "failed"

    graph = StateGraph(JDAgentState)
    graph.add_node("extract", extract_node)
    graph.add_node("normalize", normalize_node)
    graph.add_node("validate", validate_node)
    graph.add_node("repair", repair_node)
    graph.add_edge(START, "extract")
    graph.add_edge("extract", "normalize")
    graph.add_edge("normalize", "validate")
    graph.add_conditional_edges(
        "validate",
        route_after_validate,
        {"ok": END, "repair": "repair", "failed": END},
    )
    graph.add_edge("repair", "normalize")
    return graph.compile()


_default_graph: CompiledStateGraph | None = None


def get_compiled_jd_graph() -> CompiledStateGraph:
    global _default_graph
    if _default_graph is None:
        _default_graph = compile_jd_graph()
    return _default_graph


async def analyze_job_description(raw_jd: str) -> AnalyzedJobDescription:
    result = await get_compiled_jd_graph().ainvoke(_initial_state(raw_jd))
    analyzed = result.get("analyzed_jd")
    if analyzed is None:
        raise JDAnalysisError(result.get("errors") or ["JD analysis failed"])
    return analyzed
