"""remove_edge: remove edge(s) from a source node, optionally to a specific target."""

from __future__ import annotations

from typing import Any

from ..spec import load_spec, save_spec


def run(project_dir: str, from_: str, to: str | None = None) -> dict[str, Any]:
    spec = load_spec(project_dir)

    before = len(spec.edges)
    if to is None:
        spec.edges = [e for e in spec.edges if e.from_ != from_]
    else:
        spec.edges = [e for e in spec.edges if not (e.from_ == from_ and e.to == to)]
    removed = before - len(spec.edges)

    if removed == 0:
        return {"ok": False, "error": f"no matching edge found (from={from_!r}, to={to!r})"}

    save_spec(project_dir, spec)
    return {"ok": True, "removed_count": removed, "summary": spec.summary()}
