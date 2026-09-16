import pytest

from mcp_server.spec import (
    Checkpointer,
    Edge,
    GraphSpec,
    Node,
    SpecError,
    StateField,
    load_spec,
    save_spec,
    spec_path_for,
)


class TestStateField:
    def test_to_dict_omits_unset_default(self):
        f = StateField(name="x", type="str")
        assert f.to_dict() == {"name": "x", "type": "str"}

    def test_to_dict_includes_explicit_default(self):
        f = StateField(name="x", type="int", default=0, has_default=True)
        assert f.to_dict() == {"name": "x", "type": "int", "default": 0}

    def test_to_dict_includes_reducer(self):
        f = StateField(name="messages", type="list", reducer="add_messages")
        assert f.to_dict()["reducer"] == "add_messages"

    def test_from_dict_round_trip(self):
        d = {"name": "x", "type": "int", "reducer": "add", "default": 0}
        f = StateField.from_dict(d)
        assert f.to_dict() == d

    def test_from_dict_missing_name_raises(self):
        with pytest.raises(SpecError):
            StateField.from_dict({"type": "str"})

    def test_from_dict_missing_type_raises(self):
        with pytest.raises(SpecError):
            StateField.from_dict({"name": "x"})


class TestNode:
    def test_to_dict_omits_empty_config(self):
        n = Node(id="a", type="python")
        assert n.to_dict() == {"id": "a", "type": "python"}

    def test_to_dict_includes_config(self):
        n = Node(id="a", type="python", config={"function": "f"})
        assert n.to_dict()["config"] == {"function": "f"}

    def test_from_dict_defaults_type_to_python(self):
        n = Node.from_dict({"id": "a"})
        assert n.type == "python"
        assert n.config == {}

    def test_from_dict_missing_id_raises(self):
        with pytest.raises(SpecError):
            Node.from_dict({"type": "python"})


class TestEdge:
    def test_is_conditional(self):
        assert Edge(from_="a", to="b").is_conditional is False
        assert Edge(from_="a", condition="route").is_conditional is True

    def test_to_dict_simple(self):
        e = Edge(from_="a", to="b")
        assert e.to_dict() == {"from": "a", "to": "b"}

    def test_to_dict_conditional(self):
        e = Edge(from_="a", condition="route", paths={"x": "b"})
        assert e.to_dict() == {"from": "a", "condition": "route", "paths": {"x": "b"}}

    def test_from_dict_missing_from_raises(self):
        with pytest.raises(SpecError):
            Edge.from_dict({"to": "b"})


class TestCheckpointer:
    def test_default_is_none(self):
        assert Checkpointer.from_dict(None).type == "none"

    def test_from_dict_empty_dict(self):
        assert Checkpointer.from_dict({}).type == "none"

    def test_from_dict_explicit(self):
        assert Checkpointer.from_dict({"type": "memory"}).type == "memory"


class TestGraphSpec:
    def test_node_ids(self):
        spec = GraphSpec(name="x", nodes=[Node(id="a", type="python"), Node(id="b", type="python")])
        assert spec.node_ids() == {"a", "b"}

    def test_get_node(self):
        spec = GraphSpec(name="x", nodes=[Node(id="a", type="python")])
        assert spec.get_node("a") is not None
        assert spec.get_node("missing") is None

    def test_summary(self):
        spec = GraphSpec(
            name="demo",
            entry_point="a",
            nodes=[Node(id="a", type="python")],
            edges=[Edge(from_="a", to="END")],
            state=[StateField(name="x", type="str")],
        )
        assert spec.summary() == {
            "name": "demo",
            "entry_point": "a",
            "node_count": 1,
            "edge_count": 1,
            "state_field_count": 1,
            "checkpointer_type": "none",
        }

    def test_from_dict_missing_name_raises(self):
        with pytest.raises(SpecError):
            GraphSpec.from_dict({})

    def test_yaml_round_trip(self):
        spec = GraphSpec(
            name="demo",
            entry_point="a",
            nodes=[Node(id="a", type="python", config={"function": "f"})],
            edges=[Edge(from_="a", to="END")],
            state=[StateField(name="x", type="str", default="hi", has_default=True)],
            checkpointer=Checkpointer(type="memory"),
        )
        restored = GraphSpec.from_yaml(spec.to_yaml())
        assert restored == spec

    def test_from_yaml_non_mapping_raises(self):
        with pytest.raises(SpecError):
            GraphSpec.from_yaml("- just\n- a\n- list\n")

    def test_from_yaml_empty_raises(self):
        with pytest.raises(SpecError):
            GraphSpec.from_yaml("")


class TestPersistence:
    def test_save_and_load_round_trip(self, tmp_path):
        spec = GraphSpec(name="demo", entry_point="a", nodes=[Node(id="a", type="python")])
        save_spec(tmp_path, spec)
        assert spec_path_for(tmp_path).exists()
        loaded = load_spec(tmp_path)
        assert loaded == spec

    def test_load_missing_spec_raises(self, tmp_path):
        with pytest.raises(SpecError):
            load_spec(tmp_path / "does_not_exist")

    def test_save_creates_parent_dirs(self, tmp_path):
        nested = tmp_path / "a" / "b" / "c"
        save_spec(nested, GraphSpec(name="x"))
        assert spec_path_for(nested).exists()
