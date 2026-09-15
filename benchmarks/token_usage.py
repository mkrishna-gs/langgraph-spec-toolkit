"""Token-usage benchmark: full-file regeneration vs. a single spec-tool edit.

Measures the "Why" claim in the README: editing a graph through one MCP
tool call costs a roughly flat number of tokens regardless of graph size,
while asking an LLM-driven coding tool to regenerate a full graph.py scales
with the number of nodes/edges in the graph.

Tokens are counted with a small regex-based approximate tokenizer (see
`count_tokens` below) — deliberately *not* any one vendor's real BPE
tokenizer (Claude's, GPT's, Copilot's, etc. all differ, and some require a
network fetch of vendor-hosted encoding tables that isn't guaranteed to be
reachable everywhere this benchmark runs). Identifiers, numbers, string
literals, and individual punctuation/operator characters are each counted
as one token, which is the same rough granularity real subword tokenizers
use for source code. Treat the absolute numbers as approximate; treat the
*shape* of the curve — flat vs. linear — as the finding, since any
reasonable token-counting method will show the same shape.

Run:
    uv run python benchmarks/token_usage.py
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp_server.tools import add_edge, add_node, init_project, render_python

GRAPH_SIZES = [3, 5, 10, 25, 50, 100]

# One "token" per identifier/keyword, number, quoted string, or single
# punctuation/operator character. Whitespace itself isn't counted, matching
# how real subword tokenizers usually fold leading whitespace into the
# following token rather than emitting it separately.
_TOKEN_PATTERN = re.compile(
    r"[A-Za-z_][A-Za-z0-9_]*"      # identifiers / keywords
    r"|\d+\.\d+|\d+"               # numbers
    r"|\"[^\"\n]*\"|'[^'\n]*'"     # quoted strings (rough)
    r"|[^\sA-Za-z0-9_]"            # single punctuation/operator char
)


def count_tokens(text: str) -> int:
    return len(_TOKEN_PATTERN.findall(text))


def build_spec(tmp_dir: Path, n_nodes: int) -> Path:
    """A linear chain of n_nodes, each with a reducer-backed message state
    field — representative of a typical small-to-medium agent graph.
    """
    project_dir = tmp_dir / f"bench_{n_nodes}"
    init_project.run(
        project_dir=str(project_dir),
        name=f"bench_{n_nodes}",
        state_fields=[
            {"name": "messages", "type": "list[BaseMessage]", "reducer": "add_messages", "default": []}
        ],
    )
    node_ids = [f"node_{i}" for i in range(n_nodes)]
    for nid in node_ids:
        add_node.run(project_dir=str(project_dir), id=nid, config={"function": nid})
    for a, b in zip(node_ids, node_ids[1:]):
        add_edge.run(project_dir=str(project_dir), from_=a, to=b)
    add_edge.run(project_dir=str(project_dir), from_=node_ids[-1], to="END")
    return project_dir


def full_regen_tokens(project_dir: Path) -> int:
    """Token cost of the artifact a 'regenerate the whole file' approach
    would have to produce: the complete rendered graph.py.
    """
    result = render_python.run(project_dir=str(project_dir))
    assert result["ok"], result
    return count_tokens(result["code"])


def spec_edit_tokens() -> int:
    """Token cost of ONE spec edit: a single add_node tool call's arguments.

    This is independent of graph size by construction — the whole point of
    editing a spec through a tool call instead of rewriting a file.
    """
    call_args = {
        "project_dir": "my_graph",
        "id": "new_node",
        "type": "python",
        "config": {"function": "new_node"},
    }
    return count_tokens(json.dumps(call_args))


def main() -> None:
    edit_cost = spec_edit_tokens()

    header = f"{'nodes':>6} | {'full graph.py regen':>20} | {'one spec edit':>14} | {'ratio':>8}"
    print(header)
    print("-" * len(header))

    rows = []
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for n in GRAPH_SIZES:
            spec_dir = build_spec(tmp, n)
            full = full_regen_tokens(spec_dir)
            ratio = full / edit_cost
            rows.append((n, full, edit_cost, ratio))
            print(f"{n:>6} | {full:>20} | {edit_cost:>14} | {ratio:>7.1f}x")

    print()
    print("Markdown table:")
    print()
    print("| Nodes in graph | Full `graph.py` regen (tokens) | One spec edit (tokens) | Ratio |")
    print("|---:|---:|---:|---:|")
    for n, full, edit, ratio in rows:
        print(f"| {n} | {full} | {edit} | {ratio:.1f}x |")


if __name__ == "__main__":
    main()
