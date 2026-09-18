"""Generates the walkthrough shown by demo.tape / demo.gif.

Not part of the package — a script for regenerating the README demo when
tool signatures change. Run from the repo root: `uv run python .github/assets/demo.py`
"""

import shutil

from mcp_server.tools import apply_changes, init_project, render_python, validate_graph

PROJECT = "demo_graph"
shutil.rmtree(PROJECT, ignore_errors=True)

print("1) init_project - scaffold spec.yaml, nodes.py\n")
init_project.run(project_dir=PROJECT, name="demo_graph")

print("2) apply_changes - nodes + edges wired in one round trip\n")
apply_changes.run(
    project_dir=PROJECT,
    operations=[
        {"op": "add_node", "id": "greet"},
        {"op": "add_node", "id": "respond"},
        {"op": "add_edge", "from_": "greet", "to": "respond"},
        {"op": "add_edge", "from_": "respond", "to": "END"},
    ],
)

print("3) validate_graph - catch problems before any code is emitted\n")
result = validate_graph.run(project_dir=PROJECT)
print(f"   ok={result['ok']}  issues={len(result['issues'])}\n")

print("4) render_python - deterministic codegen, no LLM involved\n")
render_python.run(project_dir=PROJECT)
print(f"   wrote {PROJECT}/graph.py\n")
