"""MCP server exposing the langgraph-spec-toolkit tools.

Run with:
    uv run python -m mcp_server.server
or, once installed:
    langgraph-spec-toolkit

Note: edges use `from_` (not `from`) as the parameter name in every tool
below, since `from` is a reserved word in Python. It still serializes to
the spec's `from` key in spec.yaml.
"""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from .tools import add_edge as add_edge_tool
from .tools import add_node as add_node_tool
from .tools import get_spec as get_spec_tool
from .tools import init_project as init_project_tool
from .tools import remove_edge as remove_edge_tool
from .tools import remove_node as remove_node_tool
from .tools import render_python as render_python_tool
from .tools import set_state_schema as set_state_schema_tool
from .tools import validate_graph as validate_graph_tool

mcp = MCPServer(
    "langgraph-spec-toolkit",
    instructions=(
        "Build LangGraph projects by editing a structured spec.yaml instead of "
        "regenerating Python from scratch each turn. Call init_project once, then "
        "add_node/add_edge/set_state_schema to shape the graph, validate_graph to "
        "check it, and render_python to emit graph.py. add_node/add_edge/remove_node/"
        "remove_edge/set_state_schema return a compact summary (counts), not the full "
        "spec — call get_spec when you need the whole picture."
    ),
)


@mcp.tool()
def init_project(
    project_dir: str,
    name: str,
    state_fields: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create a new spec-driven LangGraph project: spec.yaml, nodes.py stub, __init__.py.

    project_dir: directory to create/use (created if missing; error if a
        spec.yaml already exists there).
    name: project/graph name, stored in spec.yaml.
    state_fields: optional initial state fields, each
        {name, type, reducer?, default?}.
    """
    return init_project_tool.run(project_dir=project_dir, name=name, state_fields=state_fields)


@mcp.tool()
def add_node(
    project_dir: str,
    id: str,
    type: str = "python",
    config: dict[str, Any] | None = None,
    entry_point: bool = False,
) -> dict[str, Any]:
    """Add or update a node. config['function'] names the callable in nodes.py
    (defaults to the node id if omitted).

    The first node added to a project becomes the entry point automatically;
    pass entry_point=True to (re)designate a later node instead.
    """
    return add_node_tool.run(
        project_dir=project_dir, id=id, type=type, config=config, entry_point=entry_point
    )


@mcp.tool()
def add_edge(
    project_dir: str,
    from_: str,
    to: str | None = None,
    condition: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Add an edge between nodes.

    Simple edge: set `to` (a node id, or "END").
    Conditional edge: set `condition` (the name of a router function in
    nodes.py) and `paths` (a mapping of the router's return value to a
    target node id or "END").
    """
    return add_edge_tool.run(
        project_dir=project_dir, from_=from_, to=to, condition=condition, paths=paths
    )


@mcp.tool()
def remove_node(project_dir: str, id: str) -> dict[str, Any]:
    """Remove a node, cascading to delete any edges that touch it."""
    return remove_node_tool.run(project_dir=project_dir, id=id)


@mcp.tool()
def remove_edge(project_dir: str, from_: str, to: str | None = None) -> dict[str, Any]:
    """Remove edge(s) from a source node. Omit `to` to remove all edges from that source."""
    return remove_edge_tool.run(project_dir=project_dir, from_=from_, to=to)


@mcp.tool()
def set_state_schema(project_dir: str, fields: list[dict[str, Any]]) -> dict[str, Any]:
    """Replace the graph's state schema wholesale.

    Each field: {name, type, reducer?, default?}. `type` is a raw Python
    type expression (e.g. "str", "list[str]"); `reducer` names a reducer
    function (e.g. "add_messages", or a custom name defined in reducers.py).
    """
    return set_state_schema_tool.run(project_dir=project_dir, fields=fields)


@mcp.tool()
def get_spec(project_dir: str) -> dict[str, Any]:
    """Read-only fetch of the full current spec.

    Mutating tools (add_node, add_edge, remove_node, remove_edge,
    set_state_schema) return a compact summary (counts), not the full spec,
    to keep per-edit response cost flat as the graph grows. Call this when
    you actually need the whole picture.
    """
    return get_spec_tool.run(project_dir=project_dir)


@mcp.tool()
def validate_graph(project_dir: str) -> dict[str, Any]:
    """Check the spec for unreachable nodes, missing paths to END, dangling
    conditions/edges, and duplicate/typo'd ids. Returns ok=False if any
    errors (as opposed to warnings) are found.
    """
    return validate_graph_tool.run(project_dir=project_dir)


@mcp.tool()
def render_python(project_dir: str, output_path: str | None = None) -> dict[str, Any]:
    """Render the current spec into idiomatic LangGraph Python (graph.py by default).

    Deterministic Jinja2 templating — no LLM involved, same spec always
    produces the same code. Blocks if the spec has validation errors
    (warnings still allow rendering).
    """
    return render_python_tool.run(project_dir=project_dir, output_path=output_path)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
