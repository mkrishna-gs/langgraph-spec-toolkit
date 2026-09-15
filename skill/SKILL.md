---
name: langgraph-spec-toolkit
description: Build and evolve LangGraph projects by editing a structured spec.yaml through the langgraph-spec-toolkit MCP server, instead of regenerating graph.py from scratch. Use whenever the user asks to create, extend, or modify a LangGraph state machine (add a node, rewire an edge, change the state schema, add a conditional route, add a checkpointer) in a project that has (or should have) a spec.yaml.
---

# langgraph-spec-toolkit

## Why this exists

Regenerating an entire `graph.py` on every request burns tokens and risks
silently breaking something that already worked (a dropped edge, a
mistyped state key, an orphaned node). This toolkit's MCP server exposes
the graph as structured data (`spec.yaml`) that you edit with small,
targeted tool calls. Python is a deterministic build artifact of that
spec — you never hand-write or hand-edit `graph.py`.

**Never edit `graph.py` directly.** Edit the spec via tool calls, then call
`render_python` to regenerate it. If you find yourself about to write
Python for graph wiring, stop — there's a tool call for that instead.

## Core workflow

1. **New project** → `init_project(project_dir, name, state_fields?)`.
   Creates `spec.yaml`, a `nodes.py` stub, and `__init__.py`.
2. **Shape the graph** → `add_node`, `add_edge`, `remove_node`,
   `remove_edge`, `set_state_schema`, as many calls as needed. Each is a
   small, independent edit — make one call per logical change rather than
   batching unrelated changes into one state-schema replacement.
3. **Check before generating** → `validate_graph(project_dir)`. Fix any
   `error`-severity issues (warnings are advisory and won't block codegen,
   but read them anyway — an "unreachable node" warning usually means you
   forgot an edge).
4. **Generate** → `render_python(project_dir)`. Writes `graph.py`. It will
   refuse if there are still validation errors — that's a real signal that
   something in the spec is broken, not a matter of retrying.
5. **Write the node bodies** in `<project_dir>/nodes.py` by hand — normal
   Python, not templated. Function names must match each node's
   `config.function` (or its `id` if `function` is omitted) and each
   edge's `condition`.

## Spec concepts, briefly

- **State fields** (`set_state_schema` / `init_project(state_fields=...)`):
  `{name, type, reducer?, default?}`. `type` is a raw Python type
  expression (e.g. `"list[BaseMessage]"`). Known symbols
  (`BaseMessage`, `AnyMessage`, `HumanMessage`, `AIMessage`,
  `SystemMessage`, `ToolMessage`, `ChatMessage`, and typing's `Any` /
  `Optional` / `Sequence` / `Union` / `Literal`) get auto-imported in the
  rendered file — you don't need to add imports yourself. `reducer:
  add_messages` is the standard choice for a conversation history field.
- **Nodes** (`add_node`): `id`, `type` (a free-form label, e.g. `"python"`
  or `"llm"` — not currently enforced), `config` (a dict; `config.function`
  names the callable in `nodes.py`). The *first* node added to a fresh
  project becomes `entry_point` automatically; pass `entry_point=True` to
  a later `add_node` call to change it.
- **Edges** (`add_edge`): simple (`to` is a node id or `"END"`) or
  conditional (`condition` names a router function in `nodes.py`; `paths`
  maps the router's return value to a target node id or `"END"`). The
  parameter is `from_`, not `from` — Python reserves that word — but it
  still writes to the spec's `from:` key.
- **Checkpointer**: set via `set_state_schema`... actually via the spec's
  top-level `checkpointer.type` (`none` / `memory` / `sqlite` /
  `postgres`). There's no dedicated tool for it in v0.1 — edit `spec.yaml`
  directly for this one field if needed, then re-render.

## Common requests → tool calls

- *"Add a tool-calling loop after the chatbot node"* →
  `add_edge(from_="chatbot", condition="route_after_chatbot", paths={"continue": "tools", "end": "END"})`,
  then `add_edge(from_="tools", to="chatbot")`, then write
  `route_after_chatbot` and `call_tools` (or whatever you named them) in
  `nodes.py`.
- *"Remove the summarizer node"* → `remove_node(id="summarizer")`. This
  cascades to delete edges touching it — check `validate_graph` afterward
  in case that left another node unreachable or without a path to `END`.
- *"Add conversation memory"* → make sure a `messages` state field exists
  with `reducer: add_messages`, then set `checkpointer.type: memory` in
  `spec.yaml` and re-render.
- *"The graph isn't working right"* → run `validate_graph` first before
  guessing; it catches the failure modes (unreachable nodes, dangling
  conditions, missing `END` path, typo'd ids) that are easy to introduce
  by hand and easy to miss by eye.

## What this skill does not cover (v0.1)

Diagramming, subgraphs, and multi-file projects aren't implemented yet. If
asked for those, say so rather than improvising Python for them — that
would defeat the point of keeping `graph.py` a pure build artifact.

See `../README.md` for the full spec schema reference and the worked
`../examples/simple_chatbot` example.
