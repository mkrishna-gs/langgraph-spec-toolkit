"""set_state_schema: replace the graph's state schema wholesale."""

from __future__ import annotations

from typing import Any

from ..spec import GraphSpec, StateField, load_spec, save_spec


def apply(spec: GraphSpec, fields: list[dict[str, Any]]) -> dict[str, Any]:
    """Mutate an already-loaded spec in place. Shared by run() and apply_changes."""
    spec.state = [StateField.from_dict(f) for f in fields]
    return {"state": [f.to_dict() for f in spec.state]}


def run(project_dir: str, fields: list[dict[str, Any]]) -> dict[str, Any]:
    spec = load_spec(project_dir)
    result = apply(spec, fields=fields)
    save_spec(project_dir, spec)
    return {"ok": True, "state": result["state"], "summary": spec.summary()}
