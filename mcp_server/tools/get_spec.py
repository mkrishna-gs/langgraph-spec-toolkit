"""get_spec: read-only fetch of the current spec.

The mutating tools (add_node, add_edge, ...) intentionally return a compact
summary rather than the full spec, so a long editing session doesn't pay an
O(graph size) response cost on every small change. Call this tool when an
agent actually needs the full picture — e.g. before a non-trivial edit, or
to answer "what does the graph look like right now."
"""

from __future__ import annotations

from typing import Any

from ..spec import load_spec


def run(project_dir: str) -> dict[str, Any]:
    spec = load_spec(project_dir)
    return {"ok": True, "spec": spec.to_dict(), "summary": spec.summary()}
