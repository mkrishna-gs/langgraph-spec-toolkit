"""add_node: add or update a node in the graph spec."""

from __future__ import annotations

from typing import Any

from ..spec import GraphSpec, Node, load_spec, save_spec


def apply(
    spec: GraphSpec,
    id: str,
    type: str = "python",
    config: dict[str, Any] | None = None,
    entry_point: bool = False,
) -> dict[str, Any]:
    """Mutate an already-loaded spec in place. Shared by run() and apply_changes."""
    config = config or {}

    existing = spec.get_node(id)
    if existing is not None:
        existing.type = type
        existing.config = config
        action = "updated"
    else:
        spec.nodes.append(Node(id=id, type=type, config=config))
        action = "added"

    # First node in a project becomes the entry point by default; callers
    # can also force it explicitly (e.g. to change the entry point later).
    if entry_point or spec.entry_point is None:
        spec.entry_point = id

    return {"action": action, "node": {"id": id, "type": type, "config": config}}


def run(
    project_dir: str,
    id: str,
    type: str = "python",
    config: dict[str, Any] | None = None,
    entry_point: bool = False,
) -> dict[str, Any]:
    spec = load_spec(project_dir)
    result = apply(spec, id=id, type=type, config=config, entry_point=entry_point)
    save_spec(project_dir, spec)
    return {
        "ok": True,
        "action": result["action"],
        "node": result["node"],
        "entry_point": spec.entry_point,
        "summary": spec.summary(),
    }
