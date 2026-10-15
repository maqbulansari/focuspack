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


def test_cli_strict_budget_failure(tmp_path: Path):
    # Create code that will exceed a tiny budget
    (tmp_path / "large.py").write_text("x = 1\n" * 100, encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["pack", str(tmp_path), "--budget", "5", "--strict-budget"],
    )
    assert result.exit_code == 1
    assert "strict-budget violation" in result.output


def test_cli_nonexistent_focus_error(tmp_path: Path):
    (tmp_path / "valid.py").write_text("x = 1\n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["pack", str(tmp_path), "-F", "ghost_file.py"],
    )
    assert result.exit_code == 1
    assert "ghost_file.py" in result.output


def test_cli_root_focuspack_direct_options(tmp_path: Path):
    (tmp_path / "main.py").write_text("x = 42\n", encoding="utf-8")
    runner = CliRunner()
    # Invoke without explicit 'pack' command e.g. focuspack -F main.py
    result = runner.invoke(
        cli,
        [str(tmp_path), "-F", "main.py", "--stdout"],
    )
    assert result.exit_code == 0
    assert 'path="main.py"' in result.output
    assert "x = 42" in result.output


def test_cli_strict_budget_counts_whole_rendered_output(tmp_path: Path):
    (tmp_path / "small.py").write_text("a = 1\n", encoding="utf-8")
    runner = CliRunner()
    # The file body is ~2 tokens, but whole rendered XML envelope + tree is ~40 tokens.
    # A budget of 10 tokens must fail under --strict-budget because the full rendered output exceeds it.
    result = runner.invoke(
        cli,
        ["pack", str(tmp_path), "--budget", "10", "--strict-budget"],
    )
    assert result.exit_code == 1
    assert "strict-budget violation" in result.output


def test_cli_loads_focuspack_json_config(tmp_path: Path):
    (tmp_path / "app.py").write_text("print('hello')", encoding="utf-8")
    config_file = tmp_path / ".focuspack.json"
    config_file.write_text('{"output_format": "markdown", "mode": "skeleton"}', encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["pack", str(tmp_path), "--stdout"])
    assert result.exit_code == 0
    # Must format as markdown per the .focuspack.json configuration
    assert "# Codebase Context" in result.output


def test_cli_rejects_budget_zero(tmp_path: Path):
    (tmp_path / "app.py").write_text("print('hello')", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(cli, ["pack", str(tmp_path), "--budget", "0"])
    assert result.exit_code == 1
    assert "Token budget must be greater than 0" in result.output


def test_cli_summary_unredacted_secrets(tmp_path: Path):
    (tmp_path / "key.py").write_text('KEY = "sk-123456789012345678901234567890"', encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(cli, ["pack", str(tmp_path), "--no-redact-secrets"])
    assert result.exit_code == 0
    assert "Secrets Detected (Unredacted)" in result.output
    assert "Secrets Redacted" not in result.output
