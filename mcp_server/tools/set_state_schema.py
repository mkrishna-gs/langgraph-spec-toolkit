"""set_state_schema: replace the graph's state schema wholesale."""

from __future__ import annotations

from typing import Any

from ..spec import StateField, load_spec, save_spec


def run(project_dir: str, fields: list[dict[str, Any]]) -> dict[str, Any]:
    spec = load_spec(project_dir)
    spec.state = [StateField.from_dict(f) for f in fields]
    save_spec(project_dir, spec)
    return {"ok": True, "state": [f.to_dict() for f in spec.state], "spec": spec.to_dict()}
