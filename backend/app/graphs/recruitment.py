"""Parent recruitment graph. Phase 1 composes only the JD subgraph."""

from __future__ import annotations

from typing import NotRequired, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agents.jd_agent.graph import compile_jd_graph
from app.models.job_description import AnalyzedJobDescription


class RecruitmentState(TypedDict):
    raw_jd: str
    analyzed_jd: NotRequired[AnalyzedJobDescription | None]
    errors: NotRequired[list[str]]


def compile_recruitment_graph() -> CompiledStateGraph:
    jd_subgraph = compile_jd_graph()

    async def jd_analysis_node(state: RecruitmentState) -> dict:
        result = await jd_subgraph.ainvoke(
            {
                "raw_jd": state["raw_jd"],
                "raw_extraction": None,
                "analyzed_jd": None,
                "errors": [],
                "repair_attempts": 0,
            }
        )
        return {
            "analyzed_jd": result.get("analyzed_jd"),
            "errors": result.get("errors") or [],
        }

    graph = StateGraph(RecruitmentState)
    graph.add_node("jd_analysis", jd_analysis_node)
    graph.add_edge(START, "jd_analysis")
    graph.add_edge("jd_analysis", END)
    return graph.compile()
