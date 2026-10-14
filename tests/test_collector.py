"""Tests for Collector."""

from pathlib import Path

from focuspack.collector import Collector
from focuspack.config import FocusPackConfig


def test_collector_basic(tmp_path: Path):
    # Setup mock repository files
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hello')", encoding="utf-8")
    (tmp_path / "src" / "utils.py").write_text("def helper(): pass", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Test Repo", encoding="utf-8")

    # Ignored directory
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "test.js").write_text("console.log('ignored')", encoding="utf-8")

    # Binary file
    (tmp_path / "photo.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")

    config = FocusPackConfig(root_path=str(tmp_path))
    collector = Collector(config)
    files = collector.collect()

    collected_paths = [f.relative_path for f in files]
    assert "src/main.py" in collected_paths
    assert "src/utils.py" in collected_paths
    assert "README.md" in collected_paths

    # Should ignore node_modules and binary
    assert not any("node_modules" in p for p in collected_paths)
    assert "photo.png" not in collected_paths


def test_collector_includes_and_excludes(tmp_path: Path):
    (tmp_path / "app.py").write_text("a = 1", encoding="utf-8")
    (tmp_path / "test_app.py").write_text("b = 2", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("c = 3", encoding="utf-8")

    config = FocusPackConfig(
        root_path=str(tmp_path),
        include_patterns=["*.py"],
        exclude_patterns=["test_*"],
    )
    collector = Collector(config)
    files = collector.collect()

    collected_paths = [f.relative_path for f in files]
    assert "app.py" in collected_paths
    assert "test_app.py" not in collected_paths
    assert "notes.txt" not in collected_paths


def test_collector_file_tree(tmp_path: Path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "a.py").write_text("a = 1", encoding="utf-8")

    config = FocusPackConfig(root_path=str(tmp_path))
    collector = Collector(config)
    files = collector.collect()
    tree = collector.build_file_tree(files)

    assert "pkg/" in tree
    assert "a.py" in tree
