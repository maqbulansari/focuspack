"""Tests for CLI."""

from pathlib import Path

from click.testing import CliRunner

from focuspack.cli import cli


def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "focuspack version" in result.output


def test_cli_pack_stdout(tmp_path: Path):
    (tmp_path / "sample.py").write_text("print('test')", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["pack", str(tmp_path), "--stdout"])
    assert result.exit_code == 0
    assert "sample.py" in result.output
    assert "print('test')" in result.output


def test_cli_pack_with_focus_and_task(tmp_path: Path):
    (tmp_path / "app.py").write_text("import helper\ndef main(): pass", encoding="utf-8")
    (tmp_path / "helper.py").write_text("def assist(): pass", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "pack",
            str(tmp_path),
            "--focus",
            "app.py",
            "--task",
            "bugfix",
            "--stdout",
        ],
    )
    assert result.exit_code == 0
    assert 'role="focus_target"' in result.output
    assert 'role="dependency_contract"' in result.output
    assert "<task_instruction>" in result.output
    assert "principal debugging engineer" in result.output


def test_cli_pack_with_budget(tmp_path: Path):
    (tmp_path / "a.py").write_text("def a(): pass", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["pack", str(tmp_path), "--budget", "10k", "--stdout"])
    assert result.exit_code == 0
    assert 'token_budget total_allowed="10000"' in result.output


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
    assert (tmp_path / ".focuspack.json").exists()
