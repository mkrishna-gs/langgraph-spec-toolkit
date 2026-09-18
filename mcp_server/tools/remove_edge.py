"""remove_edge: remove edge(s) from a source node, optionally to a specific target."""

from __future__ import annotations

from typing import Any

from ..spec import GraphSpec, load_spec, save_spec


def apply(spec: GraphSpec, from_: str, to: str | None = None) -> dict[str, Any]:
    """Mutate an already-loaded spec in place. Shared by run() and apply_changes."""
    before = len(spec.edges)
    if to is None:
        spec.edges = [e for e in spec.edges if e.from_ != from_]
    else:
        spec.edges = [e for e in spec.edges if not (e.from_ == from_ and e.to == to)]
    removed = before - len(spec.edges)

    if removed == 0:
        return {"error": f"no matching edge found (from={from_!r}, to={to!r})"}
    return {"removed_count": removed}


def run(project_dir: str, from_: str, to: str | None = None) -> dict[str, Any]:
    spec = load_spec(project_dir)
    result = apply(spec, from_=from_, to=to)
    if "error" in result:
        return {"ok": False, "error": result["error"]}
    save_spec(project_dir, spec)
    return {"ok": True, "removed_count": result["removed_count"], "summary": spec.summary()}
