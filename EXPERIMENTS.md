# Real-world cost experiments

This file tracks real Claude Code sessions measuring what this toolkit
actually costs to use, as evidence for the claim in the README's
[Why](README.md#why) section — real `/cost` output, not a synthetic
token-count estimate. Entries are added as the implementation changes in
ways that affect cost (a new tool, a change to how existing tools respond).

## Methodology

Each entry compares a **fresh** Claude Code session (no prior conversation
history in it — that inflates `/cost` numbers unrelated to the task) given
the same plain-language request, once with the MCP server registered and
once without (a "naive" baseline: hand-write the files directly, no
toolkit). Both sessions run in an empty directory with nothing else going
on. `/cost` is read immediately after the session completes the request.

This isn't a comprehensive benchmark across graph sizes — it's a real,
reproducible data point for one small, concrete task, tracked over time.

## 2026-09-17 — from-scratch build, `apply_changes` vs. hand-written

**Request** (identical in both sessions): *"Set up a new LangGraph project
called `demo` with a greet node and a respond node that are connected,
then generate the graph."*

| Session | Setup | Requests | Cost |
|---|---|---:|---:|
| Naive (no MCP) | Hand-write `graph.py` directly | 6 | $0.1267 |
| ~~MCP, individual calls~~ | ~~`add_node`/`add_edge` one at a time~~ | ~~9~~ | ~~$0.1825~~ |
| **MCP, `apply_changes`** | Nodes/edges wired in one batched call | **6** | **$0.1291** |

The "individual calls" row is struck through and excluded from the
headline numbers above deliberately: it measured a workflow (one MCP call
per node/edge) that no longer reflects how this toolkit is meant to be
used now that `apply_changes` exists and `skill/SKILL.md` recommends it
for exactly this kind of request. Keeping it in a current-state comparison
would be citing a stale code path as if it were still the implementation.
It's kept here, struck through, for the process notes below rather than
deleted outright, since it's what led to the fix.

**What running this live (not just reasoning about it) actually caught:**

1. **A discoverability gap.** The first live run with `apply_changes`
   available didn't use it at all — the agent defaulted to the old
   individual-call pattern despite the tool's docstring recommending
   batching. `skill/SKILL.md` at the time still said *"make one call per
   logical change rather than batching"* — directly contradicting the new
   tool's purpose. Fixed by rewriting that guidance and the worked example
   in the skill file.
2. **A validator gap.** Once explicitly told to use `apply_changes`, the
   agent's first attempt included an invalid edge from `"START"` — a
   reasonable mistake, since rendered `graph.py` contains a literal
   `workflow.add_edge(START, ...)` line, but `entry_point` is actually set
   automatically, not wired as a spec edge. The validator's error message
   for this was the generic "check for a typo" dangling-edge message,
   not specific enough to self-correct from efficiently. Fixed with a
   dedicated `explicit_start_edge` check with an actionable message.

Neither of these would have surfaced from code review or a synthetic
benchmark — they only showed up from running the actual tool in a real
agent session and reading what it did.

**Result after both fixes:** a clean re-run (explicitly told to use
`apply_changes`, matching what the skill file now recommends by default)
took 6 requests — identical to the naive session's count — and cost
$0.1291, about 1.9% more than hand-writing directly. The residual gap is
most likely the MCP tool-schema tax (10 tool definitions loaded into
context even though only 4 get called for this request), which can't be
eliminated entirely but is now a rounding error rather than the 44%
penalty the individual-call workflow carried.
