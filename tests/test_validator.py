from pathlib import Path

from mcp_server.spec import Edge, GraphSpec, Node, StateField
from mcp_server.validator import is_valid, validate

EXAMPLE_SPEC = Path(__file__).parent.parent / "examples" / "simple_chatbot" / "spec.yaml"


def codes(spec: GraphSpec) -> set[str]:
    return {i.code for i in validate(spec)}


def severities(spec: GraphSpec) -> set[str]:
    return {i.severity for i in validate(spec)}


def _linear_spec(**overrides) -> GraphSpec:
    """A minimal valid two-node linear graph: a -> b -> END."""
    defaults = dict(
        name="x",
        entry_point="a",
        nodes=[Node(id="a", type="python"), Node(id="b", type="python")],
        edges=[Edge(from_="a", to="b"), Edge(from_="b", to="END")],
    )
    defaults.update(overrides)
    return GraphSpec(**defaults)


def test_example_spec_is_valid():
    spec = GraphSpec.from_yaml(EXAMPLE_SPEC.read_text())
    issues = validate(spec)
    assert issues == []
    assert is_valid(issues)


def test_minimal_valid_spec_has_no_issues():
    assert codes(_linear_spec()) == set()


def test_duplicate_node_id():
    spec = _linear_spec(nodes=[Node(id="a", type="python"), Node(id="a", type="python")])
    assert "duplicate_node" in codes(spec)


def test_duplicate_state_field():
    spec = _linear_spec(state=[StateField(name="x", type="str"), StateField(name="x", type="int")])
    assert "duplicate_state_field" in codes(spec)


def test_unknown_checkpointer_is_warning():
    from mcp_server.spec import Checkpointer

    spec = _linear_spec(checkpointer=Checkpointer(type="redis"))
    issues = validate(spec)
    matches = [i for i in issues if i.code == "unknown_checkpointer"]
    assert len(matches) == 1
    assert matches[0].severity == "warning"
    assert is_valid(issues)  # warnings don't block


def test_missing_entry_point():
    spec = _linear_spec(entry_point=None)
    assert "missing_entry_point" in codes(spec)


def test_unknown_entry_point():
    spec = _linear_spec(entry_point="typo")
    assert "unknown_entry_point" in codes(spec)


def test_dangling_edge_source():
    spec = _linear_spec(edges=[Edge(from_="ghost", to="a")])
    assert "dangling_edge_source" in codes(spec)


def test_dangling_edge_target():
    spec = _linear_spec(edges=[Edge(from_="a", to="ghost")])
    assert "dangling_edge_target" in codes(spec)


def test_edge_with_neither_to_nor_condition():
    spec = _linear_spec(edges=[Edge(from_="a")])
    assert "dangling_edge_target" in codes(spec)


def test_dangling_condition_no_paths():
    spec = _linear_spec(edges=[Edge(from_="a", condition="route", paths=None)])
    assert "dangling_condition" in codes(spec)


def test_dangling_condition_target():
    spec = _linear_spec(
        nodes=[Node(id="a", type="python")],
        edges=[Edge(from_="a", condition="route", paths={"x": "ghost"})],
    )
    assert "dangling_condition_target" in codes(spec)


def test_unreachable_node_is_warning():
    spec = _linear_spec(
        nodes=[Node(id="a", type="python"), Node(id="b", type="python"), Node(id="orphan", type="python")],
        edges=[Edge(from_="a", to="b"), Edge(from_="b", to="END"), Edge(from_="orphan", to="END")],
    )
    issues = validate(spec)
    matches = [i for i in issues if i.code == "unreachable_node"]
    assert len(matches) == 1 and matches[0].node == "orphan"
    assert matches[0].severity == "warning"
    assert is_valid(issues)


def test_missing_end_path_is_error():
    # a can reach END directly; b (reachable from a, but with no outgoing
    # edge) can't reach END at all — only b should be flagged.
    spec = _linear_spec(edges=[Edge(from_="a", to="END"), Edge(from_="a", to="b")])
    issues = validate(spec)
    matches = [i for i in issues if i.code == "missing_end_path"]
    assert len(matches) == 1 and matches[0].node == "b"
    assert matches[0].severity == "error"
    assert not is_valid(issues)


def test_cycle_without_end_is_missing_end_path():
    spec = _linear_spec(
        nodes=[Node(id="a", type="python"), Node(id="b", type="python")],
        edges=[Edge(from_="a", to="b"), Edge(from_="b", to="a")],
    )
    assert "missing_end_path" in codes(spec)


class TestIdentifierSafety:
    """These map directly to unescaped interpolation points in the renderer
    (see renderer/render.py + templates/graph.py.jinja2): function, condition,
    state field name, and non-builtin reducer are all spliced into generated
    Python without quoting, so an invalid identifier there is a code-injection
    surface, not just a typo.
    """

    def test_invalid_function_name(self):
        spec = _linear_spec(nodes=[Node(id="a", type="python", config={"function": "f(); evil()"})])
        assert "invalid_function_name" in codes(spec)

    def test_function_defaults_to_node_id_when_omitted(self):
        # id itself must also be checked, since it's the fallback function name.
        spec = _linear_spec(nodes=[Node(id="not an identifier", type="python")], entry_point="not an identifier")
        assert "invalid_function_name" in codes(spec)

    def test_valid_function_name_is_clean(self):
        spec = _linear_spec(nodes=[Node(id="a", type="python", config={"function": "my_func_1"})])
        assert "invalid_function_name" not in codes(spec)

    def test_python_keyword_as_function_name(self):
        spec = _linear_spec(nodes=[Node(id="a", type="python", config={"function": "import"})])
        assert "invalid_function_name" in codes(spec)

    def test_invalid_condition_name(self):
        spec = _linear_spec(edges=[Edge(from_="a", condition="r(); evil()", paths={"x": "b"})])
        assert "invalid_condition_name" in codes(spec)

    def test_valid_condition_name_is_clean(self):
        spec = _linear_spec(edges=[Edge(from_="a", condition="route_it", paths={"x": "b"})])
        assert "invalid_condition_name" not in codes(spec)

    def test_invalid_state_field_name(self):
        spec = _linear_spec(state=[StateField(name="bad name; evil()", type="str")])
        assert "invalid_state_field_name" in codes(spec)

    def test_valid_state_field_name_is_clean(self):
        spec = _linear_spec(state=[StateField(name="messages", type="str")])
        assert "invalid_state_field_name" not in codes(spec)

    def test_invalid_reducer_name(self):
        spec = _linear_spec(state=[StateField(name="x", type="list", reducer="evil(); import os")])
        assert "invalid_reducer_name" in codes(spec)

    def test_builtin_reducers_are_never_flagged(self):
        for reducer in ("add_messages", "add", "operator.add"):
            spec = _linear_spec(state=[StateField(name="x", type="list", reducer=reducer)])
            assert "invalid_reducer_name" not in codes(spec)

    def test_custom_reducer_valid_identifier_is_clean(self):
        spec = _linear_spec(state=[StateField(name="x", type="list", reducer="my_custom_reducer")])
        assert "invalid_reducer_name" not in codes(spec)

    def test_invalid_state_field_type_syntax(self):
        spec = _linear_spec(state=[StateField(name="x", type="str]; import os; y=[str")])
        assert "invalid_state_field_type" in codes(spec)

    def test_complex_legitimate_type_expression_is_clean(self):
        spec = _linear_spec(state=[StateField(name="x", type="dict[str, list[Optional[int]]]")])
        assert "invalid_state_field_type" not in codes(spec)

    def test_empty_type_is_invalid(self):
        spec = _linear_spec(state=[StateField(name="x", type="")])
        assert "invalid_state_field_type" in codes(spec)
