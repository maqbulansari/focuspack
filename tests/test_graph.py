"""Tests for DependencyGraph and focus resolution."""

from pathlib import Path

from focuspack.graph import DependencyGraph, FileRole


def test_dependency_graph_traversal(tmp_path: Path):
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

    assert "client.py" in graph.nodes["service.py"].imports
    assert "service.py" in graph.nodes["client.py"].imported_by

    roles = graph.apply_focus(["service.py"], max_depth=1)
    assert roles["service.py"] == FileRole.FOCUS_TARGET
    assert roles["client.py"] == FileRole.DEPENDENCY_CONTRACT
    assert roles["unrelated.py"] == FileRole.PERIPHERAL


def test_submodule_import_from_dot(tmp_path: Path):
    # Tests: from . import models (common in requests/sessions.py)
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    sessions_file = pkg_dir / "sessions.py"
    models_file = pkg_dir / "models.py"
    init_file = pkg_dir / "__init__.py"

    sessions_file.write_text("from . import models\ndef run(): pass", encoding="utf-8")
    models_file.write_text("class Request: pass", encoding="utf-8")
    init_file.write_text("", encoding="utf-8")

    graph = DependencyGraph(tmp_path)
    graph.add_file("mypkg/sessions.py", sessions_file)
    graph.add_file("mypkg/models.py", models_file)
    graph.add_file("mypkg/__init__.py", init_file)

    graph.build_graph()

    # sessions.py must import models.py
    assert "mypkg/models.py" in graph.nodes["mypkg/sessions.py"].imports
    roles = graph.apply_focus(["mypkg/sessions.py"], max_depth=1)
    assert roles["mypkg/sessions.py"] == FileRole.FOCUS_TARGET
    assert roles["mypkg/models.py"] == FileRole.DEPENDENCY_CONTRACT


def test_submodule_import_from_app_core(tmp_path: Path):
    # Tests: from app.core import store
    app_dir = tmp_path / "app" / "core"
    app_dir.mkdir(parents=True)
    main_file = tmp_path / "app" / "main.py"
    store_file = app_dir / "store.py"
    init_core = app_dir / "__init__.py"

    main_file.write_text("from app.core import store\ndef run(): store.get()", encoding="utf-8")
    store_file.write_text("def get(): pass", encoding="utf-8")
    init_core.write_text("", encoding="utf-8")

    graph = DependencyGraph(tmp_path)
    graph.add_file("app/main.py", main_file)
    graph.add_file("app/core/store.py", store_file)
    graph.add_file("app/core/__init__.py", init_core)

    graph.build_graph()

    assert "app/core/store.py" in graph.nodes["app/main.py"].imports
    roles = graph.apply_focus(["app/main.py"], max_depth=1)
    assert roles["app/main.py"] == FileRole.FOCUS_TARGET
    assert roles["app/core/store.py"] == FileRole.DEPENDENCY_CONTRACT


def test_cyclic_import_traversal(tmp_path: Path):
    # Tests: from app import cyc_b / cyc_a cycles
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    cyc_a = app_dir / "cyc_a.py"
    cyc_b = app_dir / "cyc_b.py"

    cyc_a.write_text("from app import cyc_b\ndef a(): pass", encoding="utf-8")
    cyc_b.write_text("from app import cyc_a\ndef b(): pass", encoding="utf-8")

    graph = DependencyGraph(tmp_path)
    graph.add_file("app/cyc_a.py", cyc_a)
    graph.add_file("app/cyc_b.py", cyc_b)

    graph.build_graph()

    assert "app/cyc_b.py" in graph.nodes["app/cyc_a.py"].imports
    assert "app/cyc_a.py" in graph.nodes["app/cyc_b.py"].imports

    # Safe traversal without infinite recursion
    roles = graph.apply_focus(["app/cyc_a.py"], max_depth=2)
    assert roles["app/cyc_a.py"] == FileRole.FOCUS_TARGET
    assert roles["app/cyc_b.py"] == FileRole.DEPENDENCY_CONTRACT


def test_custom_package_roots_resolution(tmp_path: Path):
    # Tests custom layout like backend/app/service.py imported from backend/app/main.py
    backend_dir = tmp_path / "backend" / "app"
    backend_dir.mkdir(parents=True)
    main_py = backend_dir / "main.py"
    service_py = backend_dir / "service.py"

    main_py.write_text(
        "from backend.app import service\ndef run(): service.start()", encoding="utf-8"
    )
    service_py.write_text("def start(): pass", encoding="utf-8")

    graph = DependencyGraph(tmp_path)
    graph.add_file("backend/app/main.py", main_py)
    graph.add_file("backend/app/service.py", service_py)

    graph.build_graph()

    # backend/app/service.py must be in main.py imports via dynamic root discovery
    assert "backend/app/service.py" in graph.nodes["backend/app/main.py"].imports
    roles = graph.apply_focus(["backend/app/main.py"], max_depth=1)
    assert roles["backend/app/main.py"] == FileRole.FOCUS_TARGET
    assert roles["backend/app/service.py"] == FileRole.DEPENDENCY_CONTRACT


def test_basename_focus_matching_in_graph(tmp_path: Path):
    app_dir = tmp_path / "src" / "deep"
    app_dir.mkdir(parents=True)
    main_file = app_dir / "main.py"
    main_file.write_text("x = 1", encoding="utf-8")

    graph = DependencyGraph(tmp_path)
    graph.add_file("src/deep/main.py", main_file)
    graph.build_graph()

    # Specifying only 'main.py' must match 'src/deep/main.py'
    roles = graph.apply_focus(["main.py"], max_depth=1)
    assert roles["src/deep/main.py"] == FileRole.FOCUS_TARGET
