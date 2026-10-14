"""Tests for DependencyGraph and focus resolution."""

from pathlib import Path

from focuspack.graph import DependencyGraph, FileRole


def test_dependency_graph_traversal(tmp_path: Path):
    # Setup mock repository with imports
    service_file = tmp_path / "service.py"
    client_file = tmp_path / "client.py"
    unrelated_file = tmp_path / "unrelated.py"

    service_file.write_text("import client\n\ndef run(): client.connect()", encoding="utf-8")
    client_file.write_text("def connect(): pass", encoding="utf-8")
    unrelated_file.write_text("def ignore_me(): pass", encoding="utf-8")

    graph = DependencyGraph(tmp_path)
    graph.add_file("service.py", service_file)
    graph.add_file("client.py", client_file)
    graph.add_file("unrelated.py", unrelated_file)

    graph.build_graph()

    # service.py imports client.py
    assert "client.py" in graph.nodes["service.py"].imports
    assert "service.py" in graph.nodes["client.py"].imported_by

    # Apply focus on service.py
    roles = graph.apply_focus(["service.py"], max_depth=1)

    assert roles["service.py"] == FileRole.FOCUS_TARGET
    assert roles["client.py"] == FileRole.DEPENDENCY_CONTRACT
    assert roles["unrelated.py"] == FileRole.PERIPHERAL
