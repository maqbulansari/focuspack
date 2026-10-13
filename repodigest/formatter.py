"""
Output formatting module for repodigest.
Supports Markdown, XML (Claude-optimized), JSON, and Plaintext.
"""

from __future__ import annotations

import json
from enum import Enum

from repodigest.analyzer import Analyzer, RepoStats
from repodigest.collector import CollectedFile

# Language mapping for markdown code fences
EXT_TO_LANG = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "jsx",
    ".tsx": "tsx",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".md": "markdown",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".ps1": "powershell",
    ".go": "go",
    ".rs": "rust",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".java": "java",
    ".kt": "kotlin",
    ".swift": "swift",
    ".sql": "sql",
    ".xml": "xml",
    ".dockerfile": "dockerfile",
}


class OutputFormat(str, Enum):
    MARKDOWN = "markdown"
    XML = "xml"
    JSON = "json"
    PLAIN = "plain"


class Formatter:
    """Formats collected repository files into target export formats."""

    @classmethod
    def format_all(
        cls,
        files: list[CollectedFile],
        stats: RepoStats,
        file_tree: str,
        fmt: str = OutputFormat.MARKDOWN,
        include_tree: bool = True,
    ) -> str:
        """Format files and statistics according to the chosen output format."""
        fmt_lower = fmt.lower()
        if fmt_lower == OutputFormat.XML:
            return cls.to_xml(files, stats, file_tree, include_tree)
        elif fmt_lower == OutputFormat.JSON:
            return cls.to_json(files, stats, file_tree, include_tree)
        elif fmt_lower == OutputFormat.PLAIN:
            return cls.to_plain(files, stats, file_tree, include_tree)
        else:
            return cls.to_markdown(files, stats, file_tree, include_tree)

    @classmethod
    def to_markdown(
        cls,
        files: list[CollectedFile],
        stats: RepoStats,
        file_tree: str,
        include_tree: bool = True,
    ) -> str:
        """Format as rich Markdown document."""
        parts: list[str] = [
            "# Codebase Digest",
            "",
            "Generated with [repodigest](https://github.com/USER/repodigest)",
            "",
            "## Summary Metrics",
            "",
            f"- **Files Processed:** {stats.total_files:,}",
            f"- **Total Lines:** {stats.total_lines:,}",
            f"- **Estimated Tokens:** ~{stats.total_tokens:,}",
            f"- **Total Size:** {Analyzer.format_bytes(stats.total_bytes)}",
            "",
        ]

        if stats.extension_counts:
            parts.extend(
                [
                    "### Breakdown by Extension",
                    "",
                    "| Extension | Files | Lines | Est. Tokens | Size |",
                    "| :--- | :---: | :---: | :---: | :---: |",
                ]
            )
            for ext, count in sorted(stats.extension_counts.items(), key=lambda x: -x[1]):
                tokens = stats.extension_tokens.get(ext, 0)
                bytes_size = stats.extension_bytes.get(ext, 0)
                parts.append(
                    f"| `{ext}` | {count:,} | - | ~{tokens:,} | {Analyzer.format_bytes(bytes_size)} |"
                )
            parts.append("")

        if include_tree and file_tree:
            parts.extend(
                [
                    "## Directory Structure",
                    "",
                    "```text",
                    file_tree,
                    "```",
                    "",
                ]
            )

        parts.extend(
            [
                "## Files Content",
                "",
            ]
        )

        for f in files:
            lang = EXT_TO_LANG.get(f.extension, "")
            parts.extend(
                [
                    "---",
                    f"### File: `{f.relative_path}`",
                    f"> **Mode:** {f.mode.title()} | **Lines:** {f.line_count:,} | **Tokens:** ~{f.token_count:,} | **Size:** {Analyzer.format_bytes(f.byte_size)}"
                    + (
                        f" | ⚠️ **Redacted Secrets:** {f.secrets_redacted}"
                        if f.secrets_redacted
                        else ""
                    ),
                    "",
                    f"```{lang}",
                    f.content,
                    "```",
                    "",
                ]
            )

        return "\n".join(parts)

    @classmethod
    def to_xml(
        cls,
        files: list[CollectedFile],
        stats: RepoStats,
        file_tree: str,
        include_tree: bool = True,
    ) -> str:
        """Format as Claude / Anthropic optimal XML prompt structure."""
        parts: list[str] = [
            "<documents>",
            f'  <metadata total_files="{stats.total_files}" total_tokens="{stats.total_tokens}" total_bytes="{stats.total_bytes}">',
            "  </metadata>",
        ]

        if include_tree and file_tree:
            parts.extend(
                [
                    "  <file_tree>",
                    f"<![CDATA[\n{file_tree}\n]]>",
                    "  </file_tree>",
                ]
            )

        for idx, f in enumerate(files, start=1):
            parts.extend(
                [
                    f'  <document index="{idx}">',
                    f"    <source>{f.relative_path}</source>",
                    f"    <mode>{f.mode}</mode>",
                    f"    <lines>{f.line_count}</lines>",
                    f"    <tokens>{f.token_count}</tokens>",
                    "    <document_content><![CDATA[",
                    f.content,
                    "]]></document_content>",
                    "  </document>",
                ]
            )

        parts.append("</documents>")
        return "\n".join(parts)

    @classmethod
    def to_json(
        cls,
        files: list[CollectedFile],
        stats: RepoStats,
        file_tree: str,
        include_tree: bool = True,
    ) -> str:
        """Format as structured JSON."""
        data = {
            "summary": {
                "total_files": stats.total_files,
                "total_lines": stats.total_lines,
                "total_tokens": stats.total_tokens,
                "total_bytes": stats.total_bytes,
                "extension_counts": stats.extension_counts,
                "extension_tokens": stats.extension_tokens,
                "extension_bytes": stats.extension_bytes,
            },
            "directory_tree": file_tree if include_tree else None,
            "files": [
                {
                    "path": f.relative_path,
                    "extension": f.extension,
                    "mode": f.mode,
                    "lines": f.line_count,
                    "tokens": f.token_count,
                    "bytes": f.byte_size,
                    "secrets_redacted": f.secrets_redacted,
                    "content": f.content,
                }
                for f in files
            ],
        }
        return json.dumps(data, indent=2)

    @classmethod
    def to_plain(
        cls,
        files: list[CollectedFile],
        stats: RepoStats,
        file_tree: str,
        include_tree: bool = True,
    ) -> str:
        """Format as clean delimiter-separated plain text."""
        parts: list[str] = [
            "=" * 80,
            f"REPO DIGEST SUMMARY: {stats.total_files} files | ~{stats.total_tokens} tokens | {Analyzer.format_bytes(stats.total_bytes)}",
            "=" * 80,
            "",
        ]

        if include_tree and file_tree:
            parts.extend([file_tree, "", "=" * 80, ""])

        for f in files:
            parts.extend(
                [
                    f"--- FILE: {f.relative_path} (mode: {f.mode}, lines: {f.line_count}, tokens: ~{f.token_count}) ---",
                    f.content,
                    "",
                ]
            )

        return "\n".join(parts)
