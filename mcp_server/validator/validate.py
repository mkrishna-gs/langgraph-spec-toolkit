"""Static checks over a GraphSpec.

Covers the four v0.1 checks: unreachable nodes, missing END path, dangling
conditions, and state key typos (plus a handful of cheap structural checks
that fall out of the same traversal for free).
"""

from __future__ import annotations

import ast
import keyword
import re
from dataclasses import dataclass
from typing import Any

from ..spec import BUILTIN_REDUCER_NAMES, END, START, Edge, GraphSpec

Severity = str  # "error" | "warning"

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _is_valid_identifier(name: str) -> bool:
    return bool(_IDENTIFIER_RE.match(name)) and not keyword.iskeyword(name)


@dataclass
class Issue:
    severity: Severity
    code: str
    message: str
    node: str | None = None
    edge: tuple[str, str | None] | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
        }
        if self.node is not None:
            d["node"] = self.node
        if self.edge is not None:
            d["edge"] = {"from": self.edge[0], "to": self.edge[1]}
        return d


def _edge_targets(edge: Edge) -> list[str]:
    targets: list[str] = []
    if edge.to is not None:
        targets.append(edge.to)
    if edge.paths:
        targets.extend(edge.paths.values())
    return targets


def validate(spec: GraphSpec) -> list[Issue]:
    issues: list[Issue] = []
    node_ids = spec.node_ids()

    _check_duplicate_node_ids(spec, issues)
    _check_duplicate_state_fields(spec, issues)
    _check_checkpointer(spec, issues)
    entry_valid = _check_entry_point(spec, node_ids, issues)
    _check_dangling_edges(spec, node_ids, issues)
    _check_function_identifiers(spec, issues)
    _check_condition_identifiers(spec, issues)
    _check_state_field_names(spec, issues)
    _check_reducer_identifiers(spec, issues)
    _check_state_field_types(spec, issues)

    forward = _adjacency(spec, node_ids)
    reachable = _reachable_from(spec.entry_point, forward) if entry_valid else set()
    if entry_valid:
        for nid in sorted(node_ids - reachable):
            issues.append(
                Issue(
                    "warning",
                    "unreachable_node",
                    f"node '{nid}' is not reachable from entry_point '{spec.entry_point}'",
                    node=nid,
                )
            )

    can_reach_end = _can_reach_end(node_ids, forward)
    check_set = reachable if entry_valid else node_ids
    for nid in sorted(check_set - can_reach_end):
        issues.append(
            Issue("error", "missing_end_path", f"node '{nid}' has no path to END", node=nid)
        )

    return issues


def is_valid(issues: list[Issue]) -> bool:
    """True if there are no *errors* (warnings are advisory)."""
    return not any(i.severity == "error" for i in issues)


def _check_duplicate_node_ids(spec: GraphSpec, issues: list[Issue]) -> None:
    seen: set[str] = set()
    for n in spec.nodes:
        if n.id in seen:
            issues.append(
                Issue("error", "duplicate_node", f"duplicate node id '{n.id}'", node=n.id)
            )
        seen.add(n.id)


def _check_duplicate_state_fields(spec: GraphSpec, issues: list[Issue]) -> None:
    seen: set[str] = set()
    for f in spec.state:
        if f.name in seen:
            issues.append(
                Issue(
                    "error",
                    "duplicate_state_field",
                    f"duplicate state field '{f.name}'",
                )
            )
        seen.add(f.name)


def _check_checkpointer(spec: GraphSpec, issues: list[Issue]) -> None:
    if spec.checkpointer.type not in {"none", "memory", "sqlite", "postgres"}:
        issues.append(
            Issue(
                "warning",
                "unknown_checkpointer",
                f"unknown checkpointer type '{spec.checkpointer.type}' "
                "(expected one of: none, memory, sqlite, postgres)",
            )
        )


def _check_function_identifiers(spec: GraphSpec, issues: list[Issue]) -> None:
    # render_graph_python splices this straight into `nodes.<function>` with no
    # quoting — an invalid identifier here isn't just a typo, it's a way to
    # inject arbitrary code into the generated graph.py.
    for n in spec.nodes:
        function = n.config.get("function", n.id)
        if not isinstance(function, str) or not _is_valid_identifier(function):
            issues.append(
                Issue(
                    "error",
                    "invalid_function_name",
                    f"node '{n.id}' has config.function={function!r}, which isn't a "
                    "valid Python identifier — it's written as `nodes.<function>` "
                    "verbatim in the generated code",
                    node=n.id,
                )
            )


def _check_condition_identifiers(spec: GraphSpec, issues: list[Issue]) -> None:
    # Same injection concern as function names: condition becomes
    # `nodes.<condition>` verbatim in a conditional edge's router reference.
    for e in spec.edges:
        if e.condition is not None and not _is_valid_identifier(e.condition):
            issues.append(
                Issue(
                    "error",
                    "invalid_condition_name",
                    f"edge from '{e.from_}' has condition={e.condition!r}, which "
                    "isn't a valid Python identifier — it's written as "
                    "`nodes.<condition>` verbatim in the generated code",
                    edge=(e.from_, None),
                )
            )


def _check_state_field_names(spec: GraphSpec, issues: list[Issue]) -> None:
    # State field names become TypedDict attribute names verbatim
    # (`{{ f.name }}: {{ f.annotation }}`) — same injection concern.
    for f in spec.state:
        if not _is_valid_identifier(f.name):
            issues.append(
                Issue(
                    "error",
                    "invalid_state_field_name",
                    f"state field name {f.name!r} isn't a valid Python identifier "
                    "— it's written as a TypedDict attribute name verbatim",
                )
            )


def _check_reducer_identifiers(spec: GraphSpec, issues: list[Issue]) -> None:
    # Built-in reducers (add_messages, add, operator.add) are handled specially
    # by the renderer; anything else is spliced in as `reducers.<reducer>`.
    for f in spec.state:
        if f.reducer is None or f.reducer in BUILTIN_REDUCER_NAMES:
            continue
        if not _is_valid_identifier(f.reducer):
            issues.append(
                Issue(
                    "error",
                    "invalid_reducer_name",
                    f"state field '{f.name}' has reducer={f.reducer!r}, which isn't "
                    "a built-in reducer or a valid Python identifier — non-builtin "
                    "reducers are written as `reducers.<reducer>` verbatim",
                )
            )


def _check_state_field_types(spec: GraphSpec, issues: list[Issue]) -> None:
    # `type` is deliberately a raw Python type expression (e.g.
    # "list[BaseMessage]"), so we can't restrict it to an identifier — but it
    # must still parse as a single expression, not arbitrary statements, since
    # it's spliced into `Annotated[<type>, ...]` / a TypedDict annotation
    # verbatim.
    for f in spec.state:
        try:
            ast.parse(f.type, mode="eval")
        except SyntaxError:
            issues.append(
                Issue(
                    "error",
                    "invalid_state_field_type",
                    f"state field '{f.name}' has type={f.type!r}, which isn't a "
                    "valid Python expression",
                )
            )


def _check_entry_point(spec: GraphSpec, node_ids: set[str], issues: list[Issue]) -> bool:
    if not spec.entry_point:
        issues.append(Issue("error", "missing_entry_point", "spec has no entry_point set"))
        return False
    if spec.entry_point not in node_ids:
        issues.append(
            Issue(
                "error",
                "unknown_entry_point",
                f"entry_point '{spec.entry_point}' does not match any node id "
                "(check for a typo)",
                node=spec.entry_point,
            )
        )
        return False
    return True


def _check_dangling_edges(spec: GraphSpec, node_ids: set[str], issues: list[Issue]) -> None:
    for e in spec.edges:
        if e.from_ == START:
            issues.append(
                Issue(
                    "error",
                    "explicit_start_edge",
                    f"edge from {START!r} to {e.to!r} isn't needed or valid — "
                    "entry_point is set automatically (the first node added, or "
                    "pass entry_point=true on a later add_node) rather than wired "
                    "as an edge from START",
                    edge=(e.from_, e.to),
                )
            )
        elif e.from_ not in node_ids:
            issues.append(
                Issue(
                    "error",
                    "dangling_edge_source",
                    f"edge source '{e.from_}' is not a defined node (check for a typo)",
                    edge=(e.from_, e.to),
                )
            )

        if e.is_conditional:
            if not e.paths:
                issues.append(
                    Issue(
                        "error",
                        "dangling_condition",
                        f"conditional edge from '{e.from_}' (condition={e.condition!r}) "
                        "has no 'paths' mapping",
                        edge=(e.from_, None),
                    )
                )
            else:
                for label, target in e.paths.items():
                    if target != END and target not in node_ids:
                        issues.append(
                            Issue(
                                "error",
                                "dangling_condition_target",
                                f"conditional edge from '{e.from_}' path {label!r} -> "
                                f"'{target}' is not a defined node or END "
                                "(check for a typo)",
                                edge=(e.from_, target),
                            )
                        )
        else:
            if e.to is None:
                issues.append(
                    Issue(
                        "error",
                        "dangling_edge_target",
                        f"edge from '{e.from_}' has neither 'to' nor 'condition' set",
                        edge=(e.from_, None),
                    )
                )
            elif e.to != END and e.to not in node_ids:
                issues.append(
                    Issue(
                        "error",
                        "dangling_edge_target",
                        f"edge from '{e.from_}' -> '{e.to}' is not a defined node or END "
                        "(check for a typo)",
                        edge=(e.from_, e.to),
                    )
                )


def _adjacency(spec: GraphSpec, node_ids: set[str]) -> dict[str, list[str]]:
    forward: dict[str, list[str]] = {nid: [] for nid in node_ids}
    for e in spec.edges:
        if e.from_ not in forward:
            continue
        forward[e.from_].extend(t for t in _edge_targets(e) if t in node_ids or t == END)
    return forward


def _reachable_from(entry_point: str | None, forward: dict[str, list[str]]) -> set[str]:
    if entry_point is None:
        return set()
    reachable: set[str] = set()
    stack = [entry_point]
    while stack:
        cur = stack.pop()
        if cur in reachable:
            continue
        reachable.add(cur)
        stack.extend(t for t in forward.get(cur, []) if t != END)
    return reachable


def _can_reach_end(node_ids: set[str], forward: dict[str, list[str]]) -> set[str]:
    can_reach_end: set[str] = set()
    changed = True
    while changed:
        changed = False
        for nid in node_ids:
            if nid in can_reach_end:
                continue
            for t in forward.get(nid, []):
                if t == END or t in can_reach_end:
                    can_reach_end.add(nid)
                    changed = True
                    break
    return can_reach_end
