"""Data model for the LangGraph spec (spec.yaml) and its (de)serialization.

The spec is the single source of truth an LLM edits instead of regenerating
Python on every turn. Everything here is plain dataclasses + PyYAML — no
pydantic, no schema library — to keep the dependency footprint at
mcp + jinja2 + pyyaml.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

SPEC_FILENAME = "spec.yaml"
END = "END"
START = "START"

# Reducer names the renderer recognizes as built-in (see renderer/render.py's
# _BUILTIN_REDUCERS). Anything else is assumed to be a plain identifier naming
# a function in the generated project's reducers.py, and validated as such —
# see validator/validate.py's identifier checks.
BUILTIN_REDUCER_NAMES = frozenset({"add_messages", "add", "operator.add"})


class SpecError(ValueError):
    """Raised for structurally invalid spec.yaml content (bad shape, not graph semantics)."""


@dataclass
class StateField:
    name: str
    type: str
    reducer: str | None = None
    default: Any = None
    # tracks whether `default` was explicitly set (vs. None as a real default)
    has_default: bool = False

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"name": self.name, "type": self.type}
        if self.reducer is not None:
            d["reducer"] = self.reducer
        if self.has_default:
            d["default"] = self.default
        return d

    @staticmethod
    def from_dict(d: dict[str, Any]) -> StateField:
        if "name" not in d or "type" not in d:
            raise SpecError(f"state field missing 'name' or 'type': {d!r}")
        return StateField(
            name=d["name"],
            type=d["type"],
            reducer=d.get("reducer"),
            default=d.get("default"),
            has_default="default" in d,
        )


@dataclass
class Node:
    id: str
    type: str
    config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"id": self.id, "type": self.type}
        if self.config:
            d["config"] = self.config
        return d

    @staticmethod
    def from_dict(d: dict[str, Any]) -> Node:
        if "id" not in d:
            raise SpecError(f"node missing 'id': {d!r}")
        return Node(id=d["id"], type=d.get("type", "python"), config=d.get("config") or {})


@dataclass
class Edge:
    from_: str
    to: str | None = None
    condition: str | None = None
    paths: dict[str, str] | None = None

    @property
    def is_conditional(self) -> bool:
        return self.condition is not None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"from": self.from_}
        if self.to is not None:
            d["to"] = self.to
        if self.condition is not None:
            d["condition"] = self.condition
        if self.paths:
            d["paths"] = self.paths
        return d

    @staticmethod
    def from_dict(d: dict[str, Any]) -> Edge:
        if "from" not in d:
            raise SpecError(f"edge missing 'from': {d!r}")
        return Edge(
            from_=d["from"],
            to=d.get("to"),
            condition=d.get("condition"),
            paths=d.get("paths"),
        )


@dataclass
class Checkpointer:
    type: str = "none"  # none | memory | sqlite | postgres

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type}

    @staticmethod
    def from_dict(d: dict[str, Any] | None) -> Checkpointer:
        if not d:
            return Checkpointer()
        return Checkpointer(type=d.get("type", "none"))


@dataclass
class GraphSpec:
    name: str
    entry_point: str | None = None
    state: list[StateField] = field(default_factory=list)
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    checkpointer: Checkpointer = field(default_factory=Checkpointer)

    def node_ids(self) -> set[str]:
        return {n.id for n in self.nodes}

    def get_node(self, node_id: str) -> Node | None:
        return next((n for n in self.nodes if n.id == node_id), None)

    def summary(self) -> dict[str, Any]:
        """Compact counts/identity, safe to echo back on every mutating tool call
        without the O(graph size) cost of returning the full spec each time."""
        return {
            "name": self.name,
            "entry_point": self.entry_point,
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "state_field_count": len(self.state),
            "checkpointer_type": self.checkpointer.type,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "entry_point": self.entry_point,
            "state": [f.to_dict() for f in self.state],
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "checkpointer": self.checkpointer.to_dict(),
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> GraphSpec:
        if "name" not in d:
            raise SpecError("spec missing top-level 'name'")
        return GraphSpec(
            name=d["name"],
            entry_point=d.get("entry_point"),
            state=[StateField.from_dict(f) for f in d.get("state") or []],
            nodes=[Node.from_dict(n) for n in d.get("nodes") or []],
            edges=[Edge.from_dict(e) for e in d.get("edges") or []],
            checkpointer=Checkpointer.from_dict(d.get("checkpointer")),
        )

    def to_yaml(self) -> str:
        return yaml.safe_dump(self.to_dict(), sort_keys=False, default_flow_style=False)

    @staticmethod
    def from_yaml(text: str) -> GraphSpec:
        data = yaml.safe_load(text) or {}
        if not isinstance(data, dict):
            raise SpecError("spec.yaml must contain a mapping at the top level")
        return GraphSpec.from_dict(data)


def spec_path_for(project_dir: str | Path) -> Path:
    return Path(project_dir) / SPEC_FILENAME


def load_spec(project_dir: str | Path) -> GraphSpec:
    path = spec_path_for(project_dir)
    if not path.exists():
        raise SpecError(
            f"no spec.yaml found in {project_dir!s} — call init_project first"
        )
    return GraphSpec.from_yaml(path.read_text())


def save_spec(project_dir: str | Path, spec: GraphSpec) -> Path:
    path = spec_path_for(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(spec.to_yaml())
    return path
