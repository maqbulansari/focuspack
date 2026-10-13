"""
Command Line Interface for repodigest.
Powered by Click and Rich for exceptional terminal developer experience.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from repodigest import __version__
from repodigest.analyzer import Analyzer
from repodigest.clipboard import copy_to_clipboard
from repodigest.collector import Collector
from repodigest.config import RepoDigestConfig
from repodigest.formatter import Formatter

console = Console()
err_console = Console(stderr=True)


def parse_size_string(size_str: str) -> int:
    """Parse strings like '500kb', '2mb', '1024' into bytes."""
    clean = size_str.strip().lower()
    if clean.endswith(("kb", "k")):
        val = float(clean.rstrip("kb").rstrip("k"))
        return int(val * 1024)
    elif clean.endswith(("mb", "m")):
        val = float(clean.rstrip("mb").rstrip("m"))
        return int(val * 1024 * 1024)
    elif clean.endswith(("gb", "g")):
        val = float(clean.rstrip("gb").rstrip("g"))
        return int(val * 1024 * 1024 * 1024)
    return int(clean)


def render_summary_panel(stats, findings_count: int, output_dest: str = ""):
    """Render a beautiful Rich panel summarizing the digest run."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Metric", style="bold cyan")
    table.add_column("Value", style="bold white")

    table.add_row("Total Files Included", f"{stats.total_files:,}")
    table.add_row("Total Lines of Code", f"{stats.total_lines:,}")
    table.add_row("Estimated Tokens", f"~{stats.total_tokens:,}")
    table.add_row("Total Codebase Size", Analyzer.format_bytes(stats.total_bytes))

    if findings_count > 0:
        table.add_row("Secrets Redacted", f"[bold yellow]{findings_count}[/bold yellow]")

    if output_dest:
        table.add_row("Destination", f"[green]{output_dest}[/green]")

    panel = Panel(
        table,
        title=f"[bold green]repodigest v{__version__}[/bold green]",
        subtitle="[dim]Context ready for Claude, ChatGPT, Gemini[/dim]",
        border_style="green",
    )
    console.print(panel)


@click.group(invoke_without_command=True)
@click.option("--version", "-v", is_flag=True, help="Show version and exit.")
@click.pass_context
def cli(ctx: click.Context, version: bool):
    """
    [bold green]repodigest[/bold green]: Fast, intelligent codebase packaging & AST-aware context generator.
    """
    if version:
        console.print(f"[bold green]repodigest[/bold green] version [cyan]{__version__}[/cyan]")
        ctx.exit(0)

    if ctx.invoked_subcommand is None:
        ctx.invoke(pack)


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False),
    help="Output file path (defaults to digest.<format>).",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["markdown", "xml", "json", "plain"], case_sensitive=False),
    default="markdown",
    show_default=True,
    help="Target serialization format.",
)
@click.option(
    "--mode",
    "-m",
    type=click.Choice(["full", "skeleton", "auto"], case_sensitive=False),
    default="full",
    show_default=True,
    help="Code inclusion mode. 'skeleton' extracts AST signatures to save tokens.",
)
@click.option(
    "--copy",
    "-c",
    is_flag=True,
    help="Copy the generated digest directly to the system clipboard.",
)
@click.option(
    "--stdout",
    is_flag=True,
    help="Print the formatted digest directly to standard output.",
)
@click.option(
    "--diff",
    is_flag=True,
    help="Only package files with uncommitted or staged changes in git.",
)
@click.option(
    "--include",
    "-i",
    multiple=True,
    help="Glob patterns to include (e.g. '*.py', 'src/*').",
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
    help="Maximum file size to package (e.g. 500kb, 1mb).",
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
    Package repository into an optimized context document.
    """
    try:
        max_bytes = parse_size_string(max_size)
    except Exception:
        err_console.print(f"[bold red]Error:[/bold red] Invalid max-size value: {max_size}")
        sys.exit(1)

    config = RepoDigestConfig(
        root_path=path,
        output_format=format.lower(),
        mode=mode.lower(),
        max_file_size_bytes=max_bytes,
        include_patterns=list(include),
        exclude_patterns=list(exclude),
        redact_secrets=redact_secrets,
        include_tree=tree,
    )

    collector = Collector(config)
    if not quiet and not stdout:
        with console.status("[bold green]Scanning and analyzing repository...[/bold green]"):
            files = collector.collect(git_diff_only=diff)
            stats = Analyzer.compute_stats(files)
            file_tree = collector.build_file_tree(files)
    else:
        files = collector.collect(git_diff_only=diff)
        stats = Analyzer.compute_stats(files)
        file_tree = collector.build_file_tree(files)

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
    )

    # Output routing
    dest_msg = []
    if stdout:
        click.echo(output_text)
        return

    # Default output filename if not writing to stdout and not specified
    target_output_file = output
    if target_output_file is None and not copy:
        ext_map = {"markdown": "md", "xml": "xml", "json": "json", "plain": "txt"}
        target_output_file = f"digest.{ext_map.get(format.lower(), 'md')}"

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
            findings_count=len(collector.findings),
            output_dest=" & ".join(dest_msg) if dest_msg else "Done",
        )

        if collector.findings and not redact_secrets:
            console.print(
                f"[bold red]Alert:[/bold red] Found {len(collector.findings)} potential secrets in files!"
            )


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option(
    "--top",
    "-n",
    default=5,
    show_default=True,
    help="Number of largest files to display.",
)
def analyze(path: str, top: int):
    """
    Inspect codebase metrics, token counts, and language distribution.
    """
    config = RepoDigestConfig(root_path=path)
    collector = Collector(config)

    with console.status("[bold cyan]Analyzing repository metrics...[/bold cyan]"):
        files = collector.collect()
        stats = Analyzer.compute_stats(files)
        collector.build_file_tree(files)

    render_summary_panel(stats, len(collector.findings))

    # Extensions Breakdown Table
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
@click.option("--output", "-o", help="Output file path.")
@click.option("--copy", "-c", is_flag=True, help="Copy to clipboard.")
@click.pass_context
def diff(ctx: click.Context, path: str, output: str | None, copy: bool):
    """
    Package only git uncommitted and staged changes.
    """
    ctx.invoke(pack, path=path, output=output, copy=copy, diff=True)


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True, file_okay=False, dir_okay=True))
def init(path: str):
    """
    Create a .repodigest.json configuration file.
    """
    target = Path(path) / ".repodigest.json"
    if target.exists():
        console.print(f"[yellow]Configuration file already exists:[/yellow] {target}")
        return

    default_config = {
        "output_format": "markdown",
        "mode": "full",
        "max_size": "500kb",
        "include": [],
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
