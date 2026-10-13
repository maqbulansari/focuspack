"""Tests for CLI."""

from pathlib import Path

from click.testing import CliRunner

from repodigest.cli import cli


def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "repodigest version" in result.output


def test_cli_pack_stdout(tmp_path: Path):
    (tmp_path / "sample.py").write_text("print('test')", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["pack", str(tmp_path), "--stdout"])
    assert result.exit_code == 0
    assert "sample.py" in result.output
    assert "print('test')" in result.output


def test_cli_analyze(tmp_path: Path):
    (tmp_path / "sample.py").write_text("print('test')", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["analyze", str(tmp_path)])
    assert result.exit_code == 0
    assert "Total Files Included" in result.output
    assert "sample.py" in result.output


def test_cli_init(tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(cli, ["init", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / ".repodigest.json").exists()
