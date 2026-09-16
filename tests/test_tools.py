from mcp_server.spec import load_spec
from mcp_server.tools import (
    add_edge,
    add_node,
    get_spec,
    init_project,
    remove_edge,
    remove_node,
    render_python,
    set_state_schema,
    validate_graph,
)


class TestInitProject:
    def test_creates_spec_nodes_init(self, project_dir):
        result = init_project.run(project_dir=str(project_dir), name="demo")
        assert result["ok"] is True
        assert (project_dir / "spec.yaml").exists()
        assert (project_dir / "nodes.py").exists()
        assert (project_dir / "__init__.py").exists()
        assert result["summary"]["name"] == "demo"
        assert result["summary"]["node_count"] == 0
        assert "spec" not in result  # response-size fix: no full spec echoed

    def test_with_initial_state_fields(self, project_dir):
        result = init_project.run(
            project_dir=str(project_dir),
            name="demo",
            state_fields=[{"name": "messages", "type": "list", "reducer": "add_messages"}],
        )
        assert result["state"] == [{"name": "messages", "type": "list", "reducer": "add_messages"}]
        assert result["summary"]["state_field_count"] == 1

    def test_refuses_if_already_initialized(self, project_dir):
        init_project.run(project_dir=str(project_dir), name="demo")
        result = init_project.run(project_dir=str(project_dir), name="demo")
        assert result["ok"] is False
        assert "already initialized" in result["error"]

    def test_does_not_overwrite_existing_nodes_py(self, project_dir):
        project_dir.mkdir(parents=True)
        (project_dir / "nodes.py").write_text("# hand-written\n")
        # spec.yaml doesn't exist yet, so init_project proceeds
        init_project.run(project_dir=str(project_dir), name="demo")
        assert (project_dir / "nodes.py").read_text() == "# hand-written\n"


class TestAddNode:
    def test_first_node_becomes_entry_point(self, project_dir):
        init_project.run(project_dir=str(project_dir), name="demo")
        result = add_node.run(project_dir=str(project_dir), id="a")
        assert result["entry_point"] == "a"
        assert result["action"] == "added"

    def test_second_node_does_not_change_entry_point(self, project_dir):
        init_project.run(project_dir=str(project_dir), name="demo")
        add_node.run(project_dir=str(project_dir), id="a")
        result = add_node.run(project_dir=str(project_dir), id="b")
        assert result["entry_point"] == "a"

    def test_entry_point_true_reassigns(self, project_dir):
        init_project.run(project_dir=str(project_dir), name="demo")
        add_node.run(project_dir=str(project_dir), id="a")
        result = add_node.run(project_dir=str(project_dir), id="b", entry_point=True)
        assert result["entry_point"] == "b"

    def test_adding_existing_id_updates_it(self, project_dir):
        init_project.run(project_dir=str(project_dir), name="demo")
        add_node.run(project_dir=str(project_dir), id="a", config={"function": "old"})
        result = add_node.run(project_dir=str(project_dir), id="a", config={"function": "new"})
        assert result["action"] == "updated"
        spec = load_spec(project_dir)
        assert len(spec.nodes) == 1
        assert spec.get_node("a").config == {"function": "new"}

    def test_response_has_no_full_spec(self, project_dir):
        init_project.run(project_dir=str(project_dir), name="demo")
        result = add_node.run(project_dir=str(project_dir), id="a")
        assert "spec" not in result
        assert result["summary"]["node_count"] == 1


class TestAddEdge:
    def _project(self, project_dir):
        init_project.run(project_dir=str(project_dir), name="demo")
        add_node.run(project_dir=str(project_dir), id="a")
        add_node.run(project_dir=str(project_dir), id="b")
        return project_dir

    def test_simple_edge(self, project_dir):
        self._project(project_dir)
        result = add_edge.run(project_dir=str(project_dir), from_="a", to="b")
        assert result["ok"] is True
        assert result["edge"] == {"from": "a", "to": "b"}
        assert result["summary"]["edge_count"] == 1
        assert "spec" not in result

    def test_conditional_edge(self, project_dir):
        self._project(project_dir)
        result = add_edge.run(
            project_dir=str(project_dir), from_="a", condition="route", paths={"go": "b", "stop": "END"}
        )
        assert result["ok"] is True
        assert result["edge"]["condition"] == "route"

    def test_requires_to_or_condition(self, project_dir):
        self._project(project_dir)
        result = add_edge.run(project_dir=str(project_dir), from_="a")
        assert result["ok"] is False

    def test_conditional_requires_paths(self, project_dir):
        self._project(project_dir)
        result = add_edge.run(project_dir=str(project_dir), from_="a", condition="route")
        assert result["ok"] is False


class TestRemoveNode:
    def test_removes_node_and_cascades_edges(self, project_dir):
        init_project.run(project_dir=str(project_dir), name="demo")
        add_node.run(project_dir=str(project_dir), id="a")
        add_node.run(project_dir=str(project_dir), id="b")
        add_edge.run(project_dir=str(project_dir), from_="a", to="b")

        result = remove_node.run(project_dir=str(project_dir), id="b")
        assert result["ok"] is True
        assert len(result["removed_edges"]) == 1

        spec = load_spec(project_dir)
        assert spec.node_ids() == {"a"}
        assert spec.edges == []

    def test_removing_entry_point_reassigns_to_remaining_node(self, project_dir):
        init_project.run(project_dir=str(project_dir), name="demo")
        add_node.run(project_dir=str(project_dir), id="a")
        add_node.run(project_dir=str(project_dir), id="b")

        result = remove_node.run(project_dir=str(project_dir), id="a")
        assert result["entry_point"] == "b"

    def test_removing_last_node_clears_entry_point(self, project_dir):
        init_project.run(project_dir=str(project_dir), name="demo")
        add_node.run(project_dir=str(project_dir), id="a")

        result = remove_node.run(project_dir=str(project_dir), id="a")
        assert result["entry_point"] is None

    def test_removing_unknown_node_errors(self, project_dir):
        init_project.run(project_dir=str(project_dir), name="demo")
        result = remove_node.run(project_dir=str(project_dir), id="ghost")
        assert result["ok"] is False


class TestRemoveEdge:
    def _project_with_two_edges(self, project_dir):
        init_project.run(project_dir=str(project_dir), name="demo")
        add_node.run(project_dir=str(project_dir), id="a")
        add_node.run(project_dir=str(project_dir), id="b")
        add_node.run(project_dir=str(project_dir), id="c")
        add_edge.run(project_dir=str(project_dir), from_="a", to="b")
        add_edge.run(project_dir=str(project_dir), from_="a", to="c")
        return project_dir

    def test_remove_specific_target(self, project_dir):
        self._project_with_two_edges(project_dir)
        result = remove_edge.run(project_dir=str(project_dir), from_="a", to="b")
        assert result["removed_count"] == 1
        spec = load_spec(project_dir)
        assert len(spec.edges) == 1
        assert spec.edges[0].to == "c"

    def test_remove_all_from_source(self, project_dir):
        self._project_with_two_edges(project_dir)
        result = remove_edge.run(project_dir=str(project_dir), from_="a")
        assert result["removed_count"] == 2
        assert load_spec(project_dir).edges == []

    def test_remove_no_match_errors(self, project_dir):
        self._project_with_two_edges(project_dir)
        result = remove_edge.run(project_dir=str(project_dir), from_="a", to="ghost")
        assert result["ok"] is False


class TestSetStateSchema:
    def test_replaces_state_wholesale(self, project_dir):
        init_project.run(
            project_dir=str(project_dir), name="demo", state_fields=[{"name": "old", "type": "str"}]
        )
        result = set_state_schema.run(
            project_dir=str(project_dir), fields=[{"name": "new", "type": "int"}]
        )
        assert result["state"] == [{"name": "new", "type": "int"}]
        spec = load_spec(project_dir)
        assert [f.name for f in spec.state] == ["new"]


class TestGetSpec:
    def test_returns_full_spec_and_summary(self, project_dir):
        init_project.run(project_dir=str(project_dir), name="demo")
        add_node.run(project_dir=str(project_dir), id="a")
        result = get_spec.run(project_dir=str(project_dir))
        assert result["ok"] is True
        assert result["spec"]["name"] == "demo"
        assert result["spec"]["nodes"][0]["id"] == "a"
        assert result["summary"]["node_count"] == 1


class TestValidateGraph:
    def test_valid_graph(self, project_dir):
        init_project.run(project_dir=str(project_dir), name="demo")
        add_node.run(project_dir=str(project_dir), id="a")
        add_edge.run(project_dir=str(project_dir), from_="a", to="END")
        result = validate_graph.run(project_dir=str(project_dir))
        assert result["ok"] is True
        assert result["error_count"] == 0

    def test_invalid_graph_reports_errors(self, project_dir):
        init_project.run(project_dir=str(project_dir), name="demo")
        # a node with no path to END, and no entry point set explicitly wrong
        add_node.run(project_dir=str(project_dir), id="a")
        result = validate_graph.run(project_dir=str(project_dir))
        assert result["ok"] is False
        assert result["error_count"] >= 1


class TestRenderPython:
    def _valid_project(self, project_dir):
        init_project.run(project_dir=str(project_dir), name="demo")
        add_node.run(project_dir=str(project_dir), id="a")
        add_edge.run(project_dir=str(project_dir), from_="a", to="END")
        return project_dir

    def test_renders_to_default_path(self, project_dir):
        self._valid_project(project_dir)
        result = render_python.run(project_dir=str(project_dir))
        assert result["ok"] is True
        assert (project_dir / "graph.py").exists()
        assert result["output_path"] == str(project_dir / "graph.py")

    def test_renders_to_custom_path(self, project_dir):
        self._valid_project(project_dir)
        custom = project_dir / "out" / "custom_graph.py"
        result = render_python.run(project_dir=str(project_dir), output_path=str(custom))
        assert result["ok"] is True
        assert custom.exists()

    def test_blocks_on_validation_errors(self, project_dir):
        init_project.run(project_dir=str(project_dir), name="demo")
        add_node.run(project_dir=str(project_dir), id="a")  # no path to END
        result = render_python.run(project_dir=str(project_dir))
        assert result["ok"] is False
        assert not (project_dir / "graph.py").exists()

    def test_warnings_do_not_block(self, project_dir):
        init_project.run(project_dir=str(project_dir), name="demo")
        add_node.run(project_dir=str(project_dir), id="a")
        add_node.run(project_dir=str(project_dir), id="orphan")  # unreachable -> warning only
        add_edge.run(project_dir=str(project_dir), from_="a", to="END")
        add_edge.run(project_dir=str(project_dir), from_="orphan", to="END")
        result = render_python.run(project_dir=str(project_dir))
        assert result["ok"] is True
        assert len(result["warnings"]) == 1

    def test_blocks_on_unsafe_identifier(self, project_dir):
        init_project.run(project_dir=str(project_dir), name="demo")
        add_node.run(project_dir=str(project_dir), id="a", config={"function": "f(); evil()"})
        add_edge.run(project_dir=str(project_dir), from_="a", to="END")
        result = render_python.run(project_dir=str(project_dir))
        assert result["ok"] is False
        assert not (project_dir / "graph.py").exists()
