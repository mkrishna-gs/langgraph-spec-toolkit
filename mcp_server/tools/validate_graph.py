"""validate_graph: run static checks over the spec (no code emitted)."""

from __future__ import annotations

from typing import Any

from ..spec import load_spec
from ..validator import is_valid, validate


def run(project_dir: str) -> dict[str, Any]:
    spec = load_spec(project_dir)
    issues = validate(spec)
    return {
        "ok": is_valid(issues),
        "error_count": sum(1 for i in issues if i.severity == "error"),
        "warning_count": sum(1 for i in issues if i.severity == "warning"),
        "issues": [i.to_dict() for i in issues],
    }
