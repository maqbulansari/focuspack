"""
Command Line Interface for focuspack.
Focus-driven, budget-aware codebase context packager for LLMs.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from focuspack import __version__
from focuspack.analyzer import Analyzer
from focuspack.clipboard import copy_to_clipboard
from focuspack.collector import Collector
from focuspack.config import FocusPackConfig
from focuspack.formatter import Formatter
from focuspack.graph import FileRole

# Ensure UTF-8 output on Windows consoles to prevent UnicodeEncodeError with tree box characters
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

console = Console()
err_console = Console(stderr=True)


def parse_tokens_or_size(val_str: str) -> int:
    """Parse tokens like '32k', '64k', '100000', or '500kb' into integers."""
    clean = val_str.strip().lower()
    if clean.endswith("k") or clean.endswith("kb"):
        num = float(clean.rstrip("kb").rstrip("k"))
        return int(num * 1000)
    elif clean.endswith("m") or clean.endswith("mb"):
        num = float(clean.rstrip("mb").rstrip("m"))
        return int(num * 1_000_000)
    return int(clean)


def render_summary_panel(stats, collector: Collector, output_dest: str = ""):
    """Render a clean Rich panel summarizing the context run."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Metric", style="bold cyan")
    table.add_column("Value", style="bold white")

    table.add_row("Total Files Included", f"{stats.total_files:,}")
    table.add_row("Total Lines of Code", f"{stats.total_lines:,}")
    table.add_row("Estimated Tokens", f"~{stats.total_tokens:,}")
    table.add_row("Total Codebase Size", Analyzer.format_bytes(stats.total_bytes))

    # Focus and contract counts
    focus_count = sum(1 for f in collector.graph.nodes.values() if f.role == FileRole.FOCUS_TARGET)
    contract_count = sum(
        1 for f in collector.graph.nodes.values() if f.role == FileRole.DEPENDENCY_CONTRACT
    )
    if focus_count > 0:
        table.add_row("Focus Targets", f"[bold green]{focus_count}[/bold green]")
        table.add_row("Dependency Contracts", f"[bold yellow]{contract_count}[/bold yellow]")

    # Budget info
    if collector.budget_report:
        report = collector.budget_report
        b_color = "green" if report.is_within_budget else "bold red"
        table.add_row(
            "Token Budget",
            f"[{b_color}]{report.final_tokens:,} / {report.total_budget:,} ({report.utilization_pct:.1f}%)[/{b_color}]",
        )

    if collector.findings:
        table.add_row("Secrets Redacted", f"[bold red]{len(collector.findings)}[/bold red]")

    if output_dest:
        table.add_row("Destination", f"[green]{output_dest}[/green]")

    panel = Panel(
        table,
        title=f"[bold green]focuspack v{__version__}[/bold green]",
        subtitle="[dim]Focus-Driven LLM Context[/dim]",
        border_style="green"
        if (not collector.budget_report or collector.budget_report.is_within_budget)
        else "red",
    )
    console.print(panel)


@click.group(invoke_without_command=True)
@click.option("--version", "-v", is_flag=True, help="Show version and exit.")
@click.pass_context
def cli(ctx: click.Context, version: bool):
    """
    focuspack: Focus-driven, budget-aware codebase context packager for LLMs.
    """
    if version:
        console.print(f"focuspack version {__version__}")
        ctx.exit(0)

    if ctx.invoked_subcommand is None:
        ctx.invoke(pack)


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option(
    "--focus",
    "-F",
    multiple=True,
    help="Primary file(s) or directories to focus on (kept in FULL; dependencies become contracts).",
)
@click.option(
    "--depth",
    "-d",
    default=1,
    show_default=True,
    help="Dependency graph traversal depth for contracts.",
)
@click.option(
    "--include-peripherals",
    is_flag=True,
    help="Include peripheral/unrelated files in content even when focus targets are active.",
)
@click.option(
    "--budget",
    "-b",
    type=str,
    default=None,
    help="Target token budget (e.g. '32k', '64k', '128k'). Adaptively tiers files to fit.",
)
@click.option(
    "--strict-budget",
    is_flag=True,
    help="Exit with non-zero error code if output exceeds the requested token budget.",
)
@click.option(
    "--task",
    "-t",
    type=str,
    default=None,
    help="Task prompt template ('bugfix', 'review', 'refactor', 'explain', 'test', or custom prompt).",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False),
    help="Output file path (defaults to context.<format>).",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["xml", "markdown", "json", "plain"], case_sensitive=False),
    default="xml",
    show_default=True,
    help="Target serialization format (XML recommended for Claude/LLMs).",
)
@click.option(
    "--mode",
    "-m",
    type=click.Choice(["auto", "full", "skeleton"], case_sensitive=False),
    default="auto",
    show_default=True,
    help="Compression mode ('auto' tiers focus targets in full and dependencies as skeletons).",
)
@click.option(
    "--copy",
    "-c",
    is_flag=True,
    help="Copy the generated context directly to the system clipboard.",
)
@click.option(
    "--stdout",
    is_flag=True,
    help="Stream formatted context directly to standard output.",
)
@click.option(
    "--diff",
    is_flag=True,
    help="Automatically focus on uncommitted & staged git changes + their dependency contracts.",
)
@click.option(
    "--include",
    "-i",
    multiple=True,
    help="Glob patterns to include.",
)
@click.option(
    "--exclude",
    "-e",
    multiple=True,
    help="Glob patterns to exclude.",
)
@click.option(
    "--max-size",
    default="500kb",
    show_default=True,
    help="Maximum file size to package.",
)
@click.option(
    "--redact-secrets/--no-redact-secrets",
    default=True,
    show_default=True,
    help="Scan for and redact potential secrets (API keys, tokens).",
)
@click.option(
    "--tree/--no-tree",
    default=True,
    show_default=True,
    help="Include directory structure tree diagram in output.",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Suppress terminal UI and banner output.",
)
def pack(
    path: str,
    focus: tuple[str, ...],
    depth: int,
    include_peripherals: bool,
    budget: str | None,
    strict_budget: bool,
    task: str | None,
    output: str | None,
    format: str,
    mode: str,
    copy: bool,
    stdout: bool,
    diff: bool,
    include: tuple[str, ...],
    exclude: tuple[str, ...],
    max_size: str,
    redact_secrets: bool,
    tree: bool,
    quiet: bool,
):
    """
    Package focused codebase context optimized for LLMs.
    """
    try:
        max_bytes = parse_tokens_or_size(max_size)
    except Exception:
        err_console.print(f"[bold red]Error:[/bold red] Invalid max-size value: {max_size}")
        sys.exit(1)

    parsed_budget: int | None = None
    if budget:
        try:
            parsed_budget = parse_tokens_or_size(budget)
        except Exception:
            err_console.print(f"[bold red]Error:[/bold red] Invalid budget value: {budget}")
            sys.exit(1)

    config = FocusPackConfig(
        root_path=path,
        output_format=format.lower(),
        mode=mode.lower(),
        focus_targets=list(focus),
        focus_depth=depth,
        include_peripherals=include_peripherals,
        token_budget=parsed_budget,
        strict_budget=strict_budget,
        task_template=task,
        max_file_size_bytes=max_bytes,
        include_patterns=list(include),
        exclude_patterns=list(exclude),
        redact_secrets=redact_secrets,
        include_tree=tree,
    )

    collector = Collector(config)
    try:
        if not quiet and not stdout:
            with console.status(
                "[bold green]Building dependency graph and optimizing context...[/bold green]"
            ):
                files = collector.collect(git_diff_only=diff)
                stats = Analyzer.compute_stats(files)
                file_tree = collector.build_file_tree(files)
        else:
            files = collector.collect(git_diff_only=diff)
            stats = Analyzer.compute_stats(files)
            file_tree = collector.build_file_tree(files)
    except FileNotFoundError as e:
        err_console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)
    except Exception as e:
        err_console.print(f"[bold red]Unexpected error:[/bold red] {e}")
        sys.exit(1)

    if not files:
        if not quiet:
            console.print("[yellow]No matching files found to package.[/yellow]")
        sys.exit(0)

    # Format output
    output_text = Formatter.format_all(
        files=files,
        stats=stats,
        file_tree=file_tree,
        fmt=format.lower(),
        include_tree=tree,
        budget_report=collector.budget_report,
        task_prompt=task,
    )

    # Budget compliance verification
    if collector.budget_report and not collector.budget_report.is_within_budget:
        overflow_pct = collector.budget_report.utilization_pct - 100.0
        if not quiet:
            err_console.print(
                f"[bold red]Alert:[/bold red] Output exceeds target budget by {overflow_pct:.1f}% "
                f"({collector.budget_report.final_tokens:,} tokens > {collector.budget_report.total_budget:,} budget).\n"
                f"[dim]The focus target contains large implementations that could not be fully shrunk without losing API structure.[/dim]"
            )
        if strict_budget:
            err_console.print(
                "[bold red]Error:[/bold red] Exiting due to --strict-budget violation."
            )
            sys.exit(1)

    # Output routing
    dest_msg = []
    if stdout:
        click.echo(output_text)
        return

    target_output_file = output
    if target_output_file is None and not copy:
        ext_map = {"xml": "xml", "markdown": "md", "json": "json", "plain": "txt"}
        target_output_file = f"context.{ext_map.get(format.lower(), 'xml')}"

    if target_output_file:
        out_path = Path(target_output_file)
        out_path.write_text(output_text, encoding="utf-8")
        dest_msg.append(f"Saved to {out_path.resolve()}")

    if copy:
        success, msg = copy_to_clipboard(output_text)
        if success:
            dest_msg.append("Copied to clipboard")
        else:
            err_console.print(f"[yellow]Warning:[/yellow] {msg}")

    if not quiet:
        render_summary_panel(
            stats=stats,
            collector=collector,
            output_dest=" & ".join(dest_msg) if dest_msg else "Done",
        )


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option(
    "--top", "-n", default=5, show_default=True, help="Number of largest files to display."
)
def analyze(path: str, top: int):
    """
    Inspect repository dependency graph, token metrics, and largest files.
    """
    config = FocusPackConfig(root_path=path)
    collector = Collector(config)

    with console.status("[bold cyan]Analyzing repository graph and metrics...[/bold cyan]"):
        files = collector.collect()
        stats = Analyzer.compute_stats(files)

    render_summary_panel(stats, collector)

    # Extension Breakdown Table
    ext_table = Table(title="Language / Extension Breakdown", header_style="bold magenta")
    ext_table.add_column("Extension", style="cyan")
    ext_table.add_column("Files", justify="right")
    ext_table.add_column("Tokens (Est.)", justify="right")
    ext_table.add_column("Size", justify="right")

    for ext, count in sorted(
        stats.extension_counts.items(), key=lambda x: -stats.extension_tokens.get(x[0], 0)
    ):
        ext_table.add_row(
            ext,
            f"{count:,}",
            f"~{stats.extension_tokens.get(ext, 0):,}",
            Analyzer.format_bytes(stats.extension_bytes.get(ext, 0)),
        )
    console.print(ext_table)

    # Top largest files table
    if files:
        top_files = sorted(files, key=lambda f: -f.token_count)[:top]
        top_table = Table(title=f"Top {top} Largest Files by Tokens", header_style="bold yellow")
        top_table.add_column("File Path", style="dim")
        top_table.add_column("Lines", justify="right")
        top_table.add_column("Est. Tokens", justify="right", style="bold yellow")
        top_table.add_column("Size", justify="right")

        for f in top_files:
            top_table.add_row(
                f.relative_path,
                f"{f.line_count:,}",
                f"~{f.token_count:,}",
                Analyzer.format_bytes(f.byte_size),
            )
        console.print(top_table)


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option("--budget", "-b", help="Target token budget (e.g. 32k).")
@click.option("--strict-budget", is_flag=True, help="Exit with error if budget exceeded.")
@click.option("--task", "-t", help="Task prompt template.")
@click.option("--copy", "-c", is_flag=True, help="Copy to clipboard.")
@click.option("--output", "-o", help="Output file path.")
@click.pass_context
def diff(
    ctx: click.Context,
    path: str,
    budget: str | None,
    strict_budget: bool,
    task: str | None,
    copy: bool,
    output: str | None,
):
    """
    Package only git-changed files + their connected dependency contracts.
    """
    ctx.invoke(
        pack,
        path=path,
        budget=budget,
        strict_budget=strict_budget,
        task=task,
        copy=copy,
        output=output,
        diff=True,
    )


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True, file_okay=False, dir_okay=True))
def init(path: str):
    """
    Create a .focuspack.json configuration file.
    """
    target = Path(path) / ".focuspack.json"
    if target.exists():
        console.print(f"[yellow]Configuration file already exists:[/yellow] {target}")
        return

    default_config = {
        "output_format": "xml",
        "mode": "auto",
        "token_budget": 32000,
        "strict_budget": False,
        "focus_depth": 1,
        "include_peripherals": False,
        "focus_targets": [],
        "max_size": "500kb",
        "exclude": ["docs/build/**", "scratch/**"],
        "respect_gitignore": True,
        "redact_secrets": True,
        "include_tree": True,
    }
    target.write_text(json.dumps(default_config, indent=2), encoding="utf-8")
    console.print(f"[bold green]Created configuration file:[/bold green] {target}")


def main():
    """Entry point for console script."""
    cli()


if __name__ == "__main__":
    main()
