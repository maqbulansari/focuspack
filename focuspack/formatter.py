"""
Output formatting module for focuspack.
Optimized for Claude 3.5/3.7, GPT-4o, and Gemini 1.5/2.0 with semantic role tagging,
contract identification, and prompt-cache alignment.
"""

from __future__ import annotations

import json
from enum import Enum

from focuspack.analyzer import Analyzer, RepoStats
from focuspack.budget import BudgetReport
from focuspack.collector import CollectedFile
from focuspack.graph import FileRole
from focuspack.templates import get_task_instruction

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
    XML = "xml"
    MARKDOWN = "markdown"
    JSON = "json"
    PLAIN = "plain"


class Formatter:
    """Serializes codebase context into LLM-optimized formats."""

    @classmethod
    def format_all(
        cls,
        files: list[CollectedFile],
        stats: RepoStats,
        file_tree: str,
        fmt: str = OutputFormat.XML,
        include_tree: bool = True,
        budget_report: BudgetReport | None = None,
        task_prompt: str | None = None,
    ) -> str:
        """Format files and statistics according to target serialization."""
        fmt_lower = fmt.lower()
        if fmt_lower == OutputFormat.MARKDOWN:
            return cls.to_markdown(
                files, stats, file_tree, include_tree, budget_report, task_prompt
            )
        elif fmt_lower == OutputFormat.JSON:
            return cls.to_json(files, stats, file_tree, include_tree, budget_report, task_prompt)
        elif fmt_lower == OutputFormat.PLAIN:
            return cls.to_plain(files, stats, file_tree, include_tree, budget_report, task_prompt)
        else:
            return cls.to_xml(files, stats, file_tree, include_tree, budget_report, task_prompt)

    @classmethod
    def to_xml(
        cls,
        files: list[CollectedFile],
        stats: RepoStats,
        file_tree: str,
        include_tree: bool = True,
        budget_report: BudgetReport | None = None,
        task_prompt: str | None = None,
    ) -> str:
        """Generate Anthropic/Claude prompt-optimized XML with semantic roles."""
        parts: list[str] = [
            "<documents>",
            "  <context_manifest>",
            "    <tool>focuspack v0.2.0</tool>",
            f"    <total_files>{stats.total_files}</total_files>",
            f"    <total_tokens>{stats.total_tokens}</total_tokens>",
            f"    <total_size>{Analyzer.format_bytes(stats.total_bytes)}</total_size>",
        ]

        if budget_report:
            status_str = "fits" if budget_report.is_within_budget else "exceeded"
            parts.append(
                f'    <token_budget total_allowed="{budget_report.total_budget}" '
                f'tokens_used="{budget_report.final_tokens}" '
                f'utilization="{budget_report.utilization_pct:.1f}%" status="{status_str}"/>'
            )

        focus_count = sum(1 for f in files if f.role == FileRole.FOCUS_TARGET)
        contract_count = sum(1 for f in files if f.role == FileRole.DEPENDENCY_CONTRACT)
        parts.append(
            f'    <role_counts focus_targets="{focus_count}" dependency_contracts="{contract_count}"/>'
        )
        parts.append("  </context_manifest>")

        if include_tree and file_tree:
            parts.extend(
                [
                    "  <directory_structure>",
                    f"<![CDATA[\n{file_tree}\n]]>",
                    "  </directory_structure>",
                ]
            )

        parts.append("  <files>")
        for idx, f in enumerate(files, start=1):
            role_attr = f'role="{f.role.value}"'
            mode_attr = f'mode="{f.mode}"'
            imports_attr = f'imports="{", ".join(f.imports)}"' if f.imports else ""
            attrs = f'index="{idx}" path="{f.relative_path}" {role_attr} {mode_attr} tokens="{f.token_count}" {imports_attr}'.strip()

            parts.extend(
                [
                    f"    <file {attrs}>",
                    "      <document_content><![CDATA[",
                    f.content,
                    "]]></document_content>",
                    "    </file>",
                ]
            )
        parts.append("  </files>")

        instruction = get_task_instruction(task_prompt)
        if instruction:
            parts.extend(
                [
                    "  <task_instruction>",
                    f"<![CDATA[\n{instruction}\n]]>",
                    "  </task_instruction>",
                ]
            )

        parts.append("</documents>")
        return "\n".join(parts)

    @classmethod
    def to_markdown(
        cls,
        files: list[CollectedFile],
        stats: RepoStats,
        file_tree: str,
        include_tree: bool = True,
        budget_report: BudgetReport | None = None,
        task_prompt: str | None = None,
    ) -> str:
        """Generate human & AI readable Markdown."""
        parts: list[str] = [
            "# Codebase Context",
            "",
            "> Generated with [focuspack](https://github.com/USER/focuspack) — Focus-driven LLM context",
            "",
        ]

        instruction = get_task_instruction(task_prompt)
        if instruction:
            parts.extend(
                [
                    "## 🎯 Task Objective",
                    "",
                    f"> {instruction}",
                    "",
                ]
            )

        parts.extend(
            [
                "## Summary Metrics",
                "",
                f"- **Files Included:** {stats.total_files:,}",
                f"- **Total Lines:** {stats.total_lines:,}",
                f"- **Estimated Tokens:** ~{stats.total_tokens:,}",
                f"- **Total Size:** {Analyzer.format_bytes(stats.total_bytes)}",
            ]
        )

        if budget_report:
            parts.append(f"- **Token Budget:** {budget_report.summary()}")
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
                "## Codebase Files",
                "",
            ]
        )

        for f in files:
            lang = EXT_TO_LANG.get(f.extension, "")
            role_label = (
                "🎯 Focus Target"
                if f.role == FileRole.FOCUS_TARGET
                else ("📦 Contract" if f.role == FileRole.DEPENDENCY_CONTRACT else "📄 Peripheral")
            )

            parts.extend(
                [
                    "---",
                    f"### `{f.relative_path}`",
                    f"> **Role:** `{role_label}` | **Mode:** `{f.mode}` | **Tokens:** ~{f.token_count:,} | **Lines:** {f.line_count:,}"
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
    def to_json(
        cls,
        files: list[CollectedFile],
        stats: RepoStats,
        file_tree: str,
        include_tree: bool = True,
        budget_report: BudgetReport | None = None,
        task_prompt: str | None = None,
    ) -> str:
        """Format as structured JSON."""
        data = {
            "generator": "focuspack v0.2.0",
            "task": get_task_instruction(task_prompt),
            "summary": {
                "total_files": stats.total_files,
                "total_lines": stats.total_lines,
                "total_tokens": stats.total_tokens,
                "total_bytes": stats.total_bytes,
            },
            "budget": {
                "total_budget": budget_report.total_budget if budget_report else None,
                "final_tokens": budget_report.final_tokens if budget_report else stats.total_tokens,
                "is_within_budget": budget_report.is_within_budget if budget_report else True,
            }
            if budget_report
            else None,
            "directory_tree": file_tree if include_tree else None,
            "files": [
                {
                    "path": f.relative_path,
                    "role": f.role.value,
                    "mode": f.mode,
                    "tokens": f.token_count,
                    "lines": f.line_count,
                    "bytes": f.byte_size,
                    "imports": f.imports,
                    "imported_by": f.imported_by,
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
        budget_report: BudgetReport | None = None,
        task_prompt: str | None = None,
    ) -> str:
        """Format as delimiter-separated plain text."""
        parts: list[str] = [
            "=" * 80,
            f"FOCUSPACK CONTEXT: {stats.total_files} files | ~{stats.total_tokens} tokens",
            "=" * 80,
            "",
        ]

        instruction = get_task_instruction(task_prompt)
        if instruction:
            parts.extend([f"TASK: {instruction}", "", "=" * 80, ""])

        if include_tree and file_tree:
            parts.extend([file_tree, "", "=" * 80, ""])

        for f in files:
            parts.extend(
                [
                    f"--- FILE: {f.relative_path} (role: {f.role.value}, mode: {f.mode}, tokens: ~{f.token_count}) ---",
                    f.content,
                    "",
                ]
            )

        return "\n".join(parts)
