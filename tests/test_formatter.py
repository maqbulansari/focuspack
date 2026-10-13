"""Tests for Formatter."""

import json
from pathlib import Path

from repodigest.analyzer import Analyzer
from repodigest.collector import CollectedFile
from repodigest.formatter import Formatter, OutputFormat


def create_sample_file(path_str: str, content: str) -> CollectedFile:
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
        secrets_redacted=0,
    )


def test_markdown_formatter():
    files = [
        create_sample_file("main.py", "print('hello world')"),
        create_sample_file("helper.py", "def help(): pass"),
    ]
    stats = Analyzer.compute_stats(files)
    tree = "repo/\n├── main.py\n└── helper.py"

    md = Formatter.format_all(files, stats, tree, fmt=OutputFormat.MARKDOWN)
    assert "# Codebase Digest" in md
    assert "main.py" in md
    assert "helper.py" in md
    assert "```python" in md
    assert "print('hello world')" in md


def test_xml_formatter():
    files = [create_sample_file("app.py", "x = 42")]
    stats = Analyzer.compute_stats(files)
    xml = Formatter.format_all(files, stats, "", fmt=OutputFormat.XML)

    assert "<documents>" in xml
    assert "<source>app.py</source>" in xml
    assert "<document_content><![CDATA[" in xml
    assert "x = 42" in xml
    assert "</documents>" in xml


def test_json_formatter():
    files = [create_sample_file("config.json", '{"key": "value"}')]
    stats = Analyzer.compute_stats(files)
    out = Formatter.format_all(files, stats, "", fmt=OutputFormat.JSON)

    data = json.loads(out)
    assert data["summary"]["total_files"] == 1
    assert data["files"][0]["path"] == "config.json"
    assert data["files"][0]["content"] == '{"key": "value"}'
