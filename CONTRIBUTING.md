# Contributing to langgraph-spec-toolkit

Issues and pull requests are welcome. This is a young, pre-1.0 project —
the spec schema and tool signatures are still settling, so for anything
beyond a small fix, please open an issue first to discuss scope. Larger
changes are easier to land as a shared plan than as a surprise diff.

## Project layout

- `mcp_server/spec.py` — the `GraphSpec` data model (dataclasses + YAML
  (de)serialization). No pydantic, no schema library, by design.
- `mcp_server/validator/` — static checks over a `GraphSpec` (unreachable
  nodes, dangling edges, unsafe identifiers, ...).
- `mcp_server/renderer/` — deterministic Jinja2 codegen: `GraphSpec` →
  `graph.py`. No LLM calls anywhere in this path.
- `mcp_server/tools/` — one file per MCP tool (`add_node.py`, `add_edge.py`,
  ...), each exposing a plain `run(...)` function. `mcp_server/server.py`
  wires these up as MCP tools.
- `tests/` — one test file per module above, plus `test_tools.py`
  (integration tests through each tool's `run()`) and `test_server.py`
  (confirms MCP tool registration).
- `examples/simple_chatbot/` — a worked example, exercised end-to-end
  against a real `langgraph` install. `graph.py` there is a **generated
  artifact** — `tests/test_renderer.py` asserts it matches the renderer's
  output byte-for-byte, so don't hand-edit it; change `spec.yaml` and
  regenerate instead.

## Setting up

```bash
git clone https://github.com/mkrishna-gs/langgraph-spec-toolkit
cd langgraph-spec-toolkit
uv sync
```

## Before opening a PR

1. `uv sync` and confirm `uv run python -m mcp_server.server` starts
   cleanly (feed it `< /dev/null` if running it directly — it speaks MCP
   over stdio and otherwise waits for a client).
2. `uv run pytest` and `uv run ruff check .` both pass. New tools or spec
   fields need tests alongside them, in the matching `tests/test_*.py`
   file — see [`README.md`](README.md#development) for what each file
   currently covers.
3. Keep runtime dependencies to `mcp`, `jinja2`, `pyyaml` — anything else
   belongs in the *generated* project, not this toolkit. Test-only
   dependencies go in `[dependency-groups.dev]` in `pyproject.toml`.
4. Keep `render_python` deterministic: no LLM calls, no non-reproducible
   output (timestamps, random ids, unordered iteration), anywhere in the
   render path. The same `spec.yaml` must always produce byte-identical
   Python.
5. If you're adding a new field that ends up spliced into generated code
   (like `config.function` or `condition`), it needs a validator check
   requiring it to be a safe identifier — see the "Unsafe identifiers"
   checks in `mcp_server/validator/validate.py` for the existing pattern
   and why they exist.

CI (`.github/workflows/ci.yml`) runs the same lint + test steps on every
push and pull request, across Python 3.11 and 3.12.

## Reporting bugs / requesting features

Please use the issue templates — they ask for the handful of details
(spec.yaml snippet, expected vs. actual, etc.) that are usually the first
thing needed to reproduce a report, which saves a round-trip.
