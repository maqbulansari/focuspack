"""Tests for Formatter."""

import json
from pathlib import Path

from focuspack.analyzer import Analyzer
from focuspack.collector import CollectedFile
from focuspack.formatter import Formatter, OutputFormat
from focuspack.graph import FileRole


def create_sample_file(
    path_str: str, content: str, role: FileRole = FileRole.PERIPHERAL
) -> CollectedFile:
    lines = len(content.splitlines())
    byte_size = len(content.encode("utf-8"))
    tokens = Analyzer.estimate_tokens(content)
    return CollectedFile(
        relative_path=path_str,
        absolute_path=Path(path_str),
        extension=Path(path_str).suffix.lower(),
        content=content,
        line_count=lines,
        byte_size=byte_size,
        token_count=tokens,
        mode="full",
        role=role,
        secrets_redacted=0,
    )


def test_markdown_formatter():
    files = [
        create_sample_file("main.py", "print('hello world')", FileRole.FOCUS_TARGET),
        create_sample_file("helper.py", "def help(): pass", FileRole.DEPENDENCY_CONTRACT),
    ]
    stats = Analyzer.compute_stats(files)
    tree = "repo/\n├── main.py\n└── helper.py"

    md = Formatter.format_all(files, stats, tree, fmt=OutputFormat.MARKDOWN, task_prompt="review")
    assert "# Codebase Context" in md
    assert "main.py" in md
    assert "helper.py" in md
    assert "🎯 Focus Target" in md
    assert "📦 Contract" in md
    assert "senior staff code reviewer" in md


def test_xml_formatter():
    files = [create_sample_file("app.py", "x = 42", FileRole.FOCUS_TARGET)]
    stats = Analyzer.compute_stats(files)
    xml = Formatter.format_all(files, stats, "", fmt=OutputFormat.XML, task_prompt="bugfix")

    assert "<documents>" in xml
    assert '<file index="1" path="app.py" role="focus_target"' in xml
    assert "<document_content><![CDATA[" in xml
    assert "x = 42" in xml
    assert "<task_instruction>" in xml
    assert "principal debugging engineer" in xml
    assert "</documents>" in xml


def test_json_formatter():
    files = [create_sample_file("config.json", '{"key": "value"}')]
    stats = Analyzer.compute_stats(files)
    out = Formatter.format_all(files, stats, "", fmt=OutputFormat.JSON)

    data = json.loads(out)
    assert data["summary"]["total_files"] == 1
    assert data["files"][0]["path"] == "config.json"
    assert data["files"][0]["content"] == '{"key": "value"}'
