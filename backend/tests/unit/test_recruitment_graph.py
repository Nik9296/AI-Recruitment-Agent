from app.graphs.recruitment import compile_recruitment_graph


def test_parent_graph_compiles_with_jd_node() -> None:
    graph = compile_recruitment_graph()
    assert "jd_analysis" in graph.get_graph().nodes
