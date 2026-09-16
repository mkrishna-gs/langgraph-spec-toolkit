"""remove_node: remove a node and cascade-delete any edges touching it."""

from __future__ import annotations

from typing import Any

from ..spec import Edge, load_spec, save_spec


def _touches(edge: Edge, node_id: str) -> bool:
    if edge.from_ == node_id or edge.to == node_id:
        return True
    if edge.paths and node_id in edge.paths.values():
        return True
    return False


def run(project_dir: str, id: str) -> dict[str, Any]:
    spec = load_spec(project_dir)

    before = len(spec.nodes)
    spec.nodes = [n for n in spec.nodes if n.id != id]
    if len(spec.nodes) == before:
        return {"ok": False, "error": f"no node with id '{id}'"}

    removed_edges = [e for e in spec.edges if _touches(e, id)]
    spec.edges = [e for e in spec.edges if not _touches(e, id)]

    if spec.entry_point == id:
        spec.entry_point = spec.nodes[0].id if spec.nodes else None

    save_spec(project_dir, spec)
    return {
        "ok": True,
        "removed_node": id,
        "removed_edges": [e.to_dict() for e in removed_edges],
        "entry_point": spec.entry_point,
        "summary": spec.summary(),
    }
