"""Generates the walkthrough shown by demo.tape / demo.gif.

Not part of the package — a script for regenerating the README demo when
tool signatures change. Run from the repo root: `uv run python .github/assets/demo.py`
"""

import shutil

from mcp_server.tools import add_edge, add_node, init_project, render_python, validate_graph

PROJECT = "demo_graph"
shutil.rmtree(PROJECT, ignore_errors=True)

print("1) init_project - scaffold spec.yaml, nodes.py\n")
init_project.run(project_dir=PROJECT, name="demo_graph")

print("2) add_node / add_edge - small, targeted edits\n")
add_node.run(project_dir=PROJECT, id="greet", config={"function": "greet"})
add_node.run(project_dir=PROJECT, id="respond", config={"function": "respond"})
add_edge.run(project_dir=PROJECT, from_="greet", to="respond")
add_edge.run(project_dir=PROJECT, from_="respond", to="END")

print("3) validate_graph - catch problems before any code is emitted\n")
result = validate_graph.run(project_dir=PROJECT)
print(f"   ok={result['ok']}  issues={len(result['issues'])}\n")

print("4) render_python - deterministic codegen, no LLM involved\n")
render_python.run(project_dir=PROJECT)
print(f"   wrote {PROJECT}/graph.py\n")
