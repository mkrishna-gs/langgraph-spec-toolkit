from pathlib import Path

import pytest

from mcp_server.renderer.render import RenderError, render_graph_python
from mcp_server.spec import Checkpointer, Edge, GraphSpec, Node, StateField

EXAMPLE_DIR = Path(__file__).parent.parent / "examples" / "simple_chatbot"


def test_matches_committed_example_output():
    spec = GraphSpec.from_yaml((EXAMPLE_DIR / "spec.yaml").read_text())
    code = render_graph_python(spec)
    assert code == (EXAMPLE_DIR / "graph.py").read_text()


def test_missing_entry_point_raises():
    spec = GraphSpec(name="x", nodes=[Node(id="a", type="python")])
    with pytest.raises(RenderError):
        render_graph_python(spec)


def test_rendering_is_deterministic():
    spec = GraphSpec(
        name="x",
        entry_point="a",
        nodes=[Node(id="a", type="python")],
        edges=[Edge(from_="a", to="END")],
    )
    assert render_graph_python(spec) == render_graph_python(spec)


def test_simple_graph_structure():
    spec = GraphSpec(
        name="demo",
        entry_point="start",
        nodes=[Node(id="start", type="python", config={"function": "do_start"})],
        edges=[Edge(from_="start", to="END")],
    )
    code = render_graph_python(spec)
    assert "from langgraph.graph import StateGraph, START, END" in code
    assert "workflow.add_node('start', nodes.do_start)" in code
    assert "workflow.add_edge(START, 'start')" in code
    assert "workflow.add_edge('start', END)" in code
    assert "return workflow.compile()" in code
    assert "class GraphState(TypedDict):" in code
    assert "    pass" in code  # empty state


def test_node_function_defaults_to_id():
    spec = GraphSpec(
        name="x",
        entry_point="a",
        nodes=[Node(id="a", type="python")],  # no config.function
        edges=[Edge(from_="a", to="END")],
    )
    assert "nodes.a)" in render_graph_python(spec)


def test_conditional_edge_renders_paths():
    spec = GraphSpec(
        name="x",
        entry_point="a",
        nodes=[Node(id="a", type="python"), Node(id="b", type="python")],
        edges=[
            Edge(from_="a", condition="route", paths={"go": "b", "stop": "END"}),
            Edge(from_="b", to="END"),
        ],
    )
    code = render_graph_python(spec)
    assert "workflow.add_conditional_edges(" in code
    assert "nodes.route," in code
    assert "'go': 'b'," in code
    assert "'stop': END," in code


def test_builtin_reducer_add_messages_imports_correctly():
    spec = GraphSpec(
        name="x",
        entry_point="a",
        nodes=[Node(id="a", type="python")],
        edges=[Edge(from_="a", to="END")],
        state=[StateField(name="messages", type="list[BaseMessage]", reducer="add_messages")],
    )
    code = render_graph_python(spec)
    assert "from langgraph.graph.message import add_messages" in code
    assert "from langchain_core.messages import BaseMessage" in code
    assert "messages: Annotated[list[BaseMessage], add_messages]" in code


@pytest.mark.parametrize("reducer", ["add", "operator.add"])
def test_builtin_operator_add_reducer(reducer):
    spec = GraphSpec(
        name="x",
        entry_point="a",
        nodes=[Node(id="a", type="python")],
        edges=[Edge(from_="a", to="END")],
        state=[StateField(name="count", type="int", reducer=reducer)],
    )
    code = render_graph_python(spec)
    assert "import operator" in code
    assert "count: Annotated[int, operator.add]" in code


def test_custom_reducer_imports_from_reducers_module():
    spec = GraphSpec(
        name="x",
        entry_point="a",
        nodes=[Node(id="a", type="python")],
        edges=[Edge(from_="a", to="END")],
        state=[StateField(name="x", type="list", reducer="my_reducer")],
    )
    code = render_graph_python(spec)
    assert "from . import reducers" in code
    assert "x: Annotated[list, reducers.my_reducer]" in code


def test_typing_symbols_recognized_in_type_expression():
    spec = GraphSpec(
        name="x",
        entry_point="a",
        nodes=[Node(id="a", type="python")],
        edges=[Edge(from_="a", to="END")],
        state=[StateField(name="x", type="Optional[Union[int, str]]")],
    )
    code = render_graph_python(spec)
    assert "from typing import Optional, TypedDict, Union" in code


@pytest.mark.parametrize(
    "ckpt_type,expected_snippet",
    [
        ("memory", "MemorySaver()"),
        ("sqlite", "SqliteSaver.from_conn_string"),
        ("postgres", "PostgresSaver.from_conn_string"),
    ],
)
def test_checkpointer_variants(ckpt_type, expected_snippet):
    spec = GraphSpec(
        name="x",
        entry_point="a",
        nodes=[Node(id="a", type="python")],
        edges=[Edge(from_="a", to="END")],
        checkpointer=Checkpointer(type=ckpt_type),
    )
    code = render_graph_python(spec)
    assert expected_snippet in code
    assert "return workflow.compile(checkpointer=checkpointer)" in code


def test_no_checkpointer_compiles_without_one():
    spec = GraphSpec(
        name="x",
        entry_point="a",
        nodes=[Node(id="a", type="python")],
        edges=[Edge(from_="a", to="END")],
    )
    code = render_graph_python(spec)
    assert "return workflow.compile()" in code
    assert "checkpointer" not in code


def test_unknown_checkpointer_type_is_ignored_by_renderer():
    # validate_graph would warn about this; render_graph_python itself just
    # falls back to no checkpointer since "redis" isn't in the known map.
    spec = GraphSpec(
        name="x",
        entry_point="a",
        nodes=[Node(id="a", type="python")],
        edges=[Edge(from_="a", to="END")],
        checkpointer=Checkpointer(type="redis"),
    )
    code = render_graph_python(spec)
    assert "return workflow.compile()" in code
