"""Deterministic spec -> Python codegen.

No LLM in this path: every code fragment is either a fixed template line or
a mechanical transform of spec data (repr()'d literals, sorted imports).
Same spec.yaml in, byte-identical graph.py out.

Node callables and condition/router functions are *not* generated — they're
plain Python the developer writes in `nodes.py` next to the generated
`graph.py`, referenced by name from the spec. Codegen only owns topology,
state schema, and wiring.
"""

from __future__ import annotations

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from ..spec import END, GraphSpec

TEMPLATES_DIR = Path(__file__).parent / "templates"

_IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

# Symbols that commonly show up in `type:` strings but aren't builtins.
# Scanned for by name so a field like `type: list[BaseMessage]` gets its
# import pulled in automatically instead of producing a NameError at runtime.
_TYPING_SYMBOLS = {"Any", "Optional", "Sequence", "Union", "Literal"}
_LANGCHAIN_MESSAGE_SYMBOLS = {
    "BaseMessage",
    "AnyMessage",
    "HumanMessage",
    "AIMessage",
    "SystemMessage",
    "ToolMessage",
    "ChatMessage",
}

# reducer name -> (import line, expression to use in Annotated[...])
_BUILTIN_REDUCERS: dict[str, tuple[str, str]] = {
    "add_messages": ("from langgraph.graph.message import add_messages", "add_messages"),
    "add": ("import operator", "operator.add"),
    "operator.add": ("import operator", "operator.add"),
}

# checkpointer.type -> (import line, constructor expression)
_CHECKPOINTER_IMPORTS: dict[str, tuple[str, str]] = {
    "memory": ("from langgraph.checkpoint.memory import MemorySaver", "MemorySaver()"),
    "sqlite": (
        "from langgraph.checkpoint.sqlite import SqliteSaver",
        # from_conn_string() is a context manager upstream; this inline call
        # is a v0.1 placeholder — wire it to your app's lifecycle for real use.
        'SqliteSaver.from_conn_string("checkpoints.sqlite")',
    ),
    "postgres": (
        "from langgraph.checkpoint.postgres import PostgresSaver",
        'PostgresSaver.from_conn_string("<POSTGRES_CONNECTION_STRING>")',
    ),
}


def _target_literal(target: str) -> str:
    return "END" if target == END else repr(target)


def _reducer_import_and_expr(reducer: str) -> tuple[str | None, str]:
    if reducer in _BUILTIN_REDUCERS:
        return _BUILTIN_REDUCERS[reducer]
    # unrecognized reducer name: assume a user-supplied function in reducers.py
    return "from . import reducers", f"reducers.{reducer}"


def _dedup(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


class RenderError(ValueError):
    """Raised when a spec can't be rendered into valid Python (e.g. no entry_point)."""


def render_graph_python(spec: GraphSpec) -> str:
    if not spec.entry_point:
        raise RenderError(
            "spec has no entry_point set — call set_state_schema/add_node first, "
            "then set entry_point, or run validate_graph for the full list of issues"
        )

    extra_imports: list[str] = []

    typing_names: set[str] = {"TypedDict"}
    if any(f.reducer for f in spec.state):
        typing_names.add("Annotated")
    langchain_message_names: set[str] = set()

    state_fields = []
    for f in spec.state:
        for identifier in _IDENTIFIER_RE.findall(f.type):
            if identifier in _TYPING_SYMBOLS:
                typing_names.add(identifier)
            elif identifier in _LANGCHAIN_MESSAGE_SYMBOLS:
                langchain_message_names.add(identifier)

        if f.reducer:
            imp, expr = _reducer_import_and_expr(f.reducer)
            if imp:
                extra_imports.append(imp)
            annotation = f"Annotated[{f.type}, {expr}]"
        else:
            annotation = f.type
        state_fields.append({"name": f.name, "annotation": annotation})

    if langchain_message_names:
        extra_imports.append(
            "from langchain_core.messages import " + ", ".join(sorted(langchain_message_names))
        )

    if spec.nodes or any(e.is_conditional for e in spec.edges):
        extra_imports.append("from . import nodes")

    node_ctx = [
        {"id_literal": repr(n.id), "function": n.config.get("function", n.id)}
        for n in spec.nodes
    ]

    simple_edges = []
    conditional_edges = []
    for e in spec.edges:
        if e.is_conditional:
            conditional_edges.append(
                {
                    "from_literal": repr(e.from_),
                    "condition_ref": f"nodes.{e.condition}",
                    "paths": [
                        (repr(label), _target_literal(target))
                        for label, target in (e.paths or {}).items()
                    ],
                }
            )
        else:
            simple_edges.append(
                {"from_literal": repr(e.from_), "to_literal": _target_literal(e.to)}
            )

    checkpointer_instantiate = None
    if spec.checkpointer.type in _CHECKPOINTER_IMPORTS:
        imp, expr = _CHECKPOINTER_IMPORTS[spec.checkpointer.type]
        extra_imports.append(imp)
        checkpointer_instantiate = expr

    imports = [
        "from langgraph.graph import StateGraph, START, END",
        f"from typing import {', '.join(sorted(typing_names))}",
    ] + _dedup(extra_imports)

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )
    template = env.get_template("graph.py.jinja2")
    return template.render(
        spec_name=spec.name,
        state_class_name="GraphState",
        imports=imports,
        state_fields=state_fields,
        nodes=node_ctx,
        entry_point_literal=repr(spec.entry_point) if spec.entry_point else None,
        simple_edges=simple_edges,
        conditional_edges=conditional_edges,
        checkpointer_instantiate=checkpointer_instantiate,
    )
