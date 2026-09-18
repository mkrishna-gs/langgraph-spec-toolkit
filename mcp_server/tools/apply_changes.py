"""apply_changes: apply multiple spec edits in one call instead of one per edit.

Delegates each operation to the same apply() function its single-op tool
uses (add_node.apply, add_edge.apply, ...) — this is the only place that
owns per-op required-field checks and sequencing; the mutation logic itself
has one source of truth shared with add_node/add_edge/remove_node/
remove_edge/set_state_schema, so a bug fix or behavior change to one of
those can't silently drift out of sync with what a batch does for the same
operation.

Applied in-memory against a single loaded spec; nothing is written to disk
(spec.yaml unchanged) unless every operation succeeds — a bad operation
partway through aborts the whole batch cleanly, since save_spec is only
reached after the loop completes without error.
"""

from __future__ import annotations

from typing import Any

from ..spec import GraphSpec, load_spec, save_spec
from . import add_edge, add_node, remove_edge, remove_node, set_state_schema


def _do_add_node(spec: GraphSpec, op: dict[str, Any]) -> dict[str, Any]:
    if not op.get("id"):
        return {"error": "add_node needs 'id'"}
    return add_node.apply(
        spec,
        id=op["id"],
        type=op.get("type", "python"),
        config=op.get("config"),
        entry_point=op.get("entry_point", False),
    )


def _do_add_edge(spec: GraphSpec, op: dict[str, Any]) -> dict[str, Any]:
    if not op.get("from_"):
        return {"error": "add_edge needs 'from_'"}
    return add_edge.apply(
        spec,
        from_=op["from_"],
        to=op.get("to"),
        condition=op.get("condition"),
        paths=op.get("paths"),
    )


def _do_remove_node(spec: GraphSpec, op: dict[str, Any]) -> dict[str, Any]:
    if not op.get("id"):
        return {"error": "remove_node needs 'id'"}
    return remove_node.apply(spec, id=op["id"])


def _do_remove_edge(spec: GraphSpec, op: dict[str, Any]) -> dict[str, Any]:
    if not op.get("from_"):
        return {"error": "remove_edge needs 'from_'"}
    return remove_edge.apply(spec, from_=op["from_"], to=op.get("to"))


def _do_set_state_schema(spec: GraphSpec, op: dict[str, Any]) -> dict[str, Any]:
    if op.get("fields") is None:
        return {"error": "set_state_schema needs 'fields'"}
    return set_state_schema.apply(spec, fields=op["fields"])


_HANDLERS = {
    "add_node": _do_add_node,
    "add_edge": _do_add_edge,
    "remove_node": _do_remove_node,
    "remove_edge": _do_remove_edge,
    "set_state_schema": _do_set_state_schema,
}


def run(project_dir: str, operations: list[dict[str, Any]]) -> dict[str, Any]:
    spec = load_spec(project_dir)
    results: list[dict[str, Any]] = []

    for i, op in enumerate(operations):
        op_name = op.get("op")
        if op_name not in _HANDLERS:
            return {
                "ok": False,
                "error": f"operation {i} ({op_name!r}): unknown op "
                f"(expected one of {sorted(_HANDLERS)})",
            }
        outcome = _HANDLERS[op_name](spec, op)
        if "error" in outcome:
            return {"ok": False, "error": f"operation {i} ({op_name!r}): {outcome['error']}"}
        results.append(outcome)

    save_spec(project_dir, spec)
    return {"ok": True, "applied": len(results), "results": results, "summary": spec.summary()}
