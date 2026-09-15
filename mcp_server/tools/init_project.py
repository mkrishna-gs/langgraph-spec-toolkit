"""init_project: scaffold a new spec-driven LangGraph project directory."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..spec import GraphSpec, StateField, save_spec, spec_path_for

_NODES_STUB = '''"""Node and router functions for {name}.

Each function referenced from spec.yaml (a node's `config.function`, or an
edge's `condition`) must exist here under a matching name. Node functions
take the graph state dict and return a partial state update; router
functions take the state and return a label used to pick a path in the
edge's `paths` mapping. Regenerate graph.py with the `render_python` tool
after adding functions here or editing spec.yaml.
"""
'''


def run(
    project_dir: str,
    name: str,
    state_fields: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    path = Path(project_dir)
    if spec_path_for(path).exists():
        return {
            "ok": False,
            "error": (
                f"spec.yaml already exists at {spec_path_for(path)} — "
                "this project is already initialized"
            ),
        }

    path.mkdir(parents=True, exist_ok=True)

    spec = GraphSpec(
        name=name,
        state=[StateField.from_dict(f) for f in (state_fields or [])],
    )
    spec_file = save_spec(path, spec)

    init_file = path / "__init__.py"
    if not init_file.exists():
        init_file.write_text("")

    nodes_file = path / "nodes.py"
    if not nodes_file.exists():
        nodes_file.write_text(_NODES_STUB.format(name=name))

    return {
        "ok": True,
        "project_dir": str(path),
        "spec_path": str(spec_file),
        "nodes_path": str(nodes_file),
        "spec": spec.to_dict(),
    }
