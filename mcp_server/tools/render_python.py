"""render_python: deterministically emit graph.py from the current spec.

Blocks on validation *errors* (spec is structurally broken); validation
*warnings* (e.g. an unreachable node) are surfaced but don't block codegen.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..renderer import render_graph_python
from ..spec import load_spec
from ..validator import validate


def run(project_dir: str, output_path: str | None = None) -> dict[str, Any]:
    spec = load_spec(project_dir)
    issues = validate(spec)
    errors = [i.to_dict() for i in issues if i.severity == "error"]
    if errors:
        return {
            "ok": False,
            "error": "spec has validation errors — call validate_graph for details",
            "issues": errors,
        }

    code = render_graph_python(spec)
    out_path = Path(output_path) if output_path else Path(project_dir) / "graph.py"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(code)

    return {
        "ok": True,
        "output_path": str(out_path),
        "warnings": [i.to_dict() for i in issues if i.severity == "warning"],
        "code": code,
    }
