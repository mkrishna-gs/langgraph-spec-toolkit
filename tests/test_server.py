import asyncio

from mcp_server.server import mcp

EXPECTED_TOOLS = {
    "init_project",
    "add_node",
    "add_edge",
    "remove_node",
    "remove_edge",
    "set_state_schema",
    "get_spec",
    "validate_graph",
    "render_python",
}


def test_all_tools_registered():
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert names == EXPECTED_TOOLS
