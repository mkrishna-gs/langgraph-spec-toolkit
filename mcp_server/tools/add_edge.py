"""add_edge: add a simple or conditional edge to the graph spec.

A simple edge sets `to`. A conditional edge sets `condition` (the name of a
router function in nodes.py) and `paths` (a mapping of the router's return
value to a target node id or "END").
"""

from __future__ import annotations

from typing import Any

from ..spec import Edge, GraphSpec, load_spec, save_spec


def apply(
    spec: GraphSpec,
    from_: str,
    to: str | None = None,
    condition: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Mutate an already-loaded spec in place. Shared by run() and apply_changes.
    Returns {"error": ...} instead of mutating if the edge is malformed.
    """
    if condition is None and to is None:
        return {"error": "edge needs either 'to' or 'condition' + 'paths'"}
    if condition is not None and not paths:
        return {"error": "conditional edge ('condition' set) requires 'paths'"}

    edge = Edge(from_=from_, to=to, condition=condition, paths=paths)
    spec.edges.append(edge)
    return {"edge": edge.to_dict()}


def run(
    project_dir: str,
    from_: str,
    to: str | None = None,
    condition: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    spec = load_spec(project_dir)
    result = apply(spec, from_=from_, to=to, condition=condition, paths=paths)
    if "error" in result:
        return {"ok": False, "error": result["error"]}
    save_spec(project_dir, spec)
    return {"ok": True, "edge": result["edge"], "summary": spec.summary()}
