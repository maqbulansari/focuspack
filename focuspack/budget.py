"""
Adaptive token budgeting engine for focuspack.
Dynamically tiers, contracts, and compresses code to fit strictly within the model's
context window, with AST-level method body compression when targets exceed budget.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from focuspack.analyzer import Analyzer
from focuspack.ast_parser import ASTParser
from focuspack.graph import FileRole

if TYPE_CHECKING:
    from focuspack.collector import CollectedFile


@dataclass
class BudgetReport:
    """Report detailing how context was adapted to satisfy the token budget."""

    total_budget: int
    initial_tokens: int
    final_tokens: int
    utilization_pct: float = 0.0
    downgraded_to_skeleton: list[str] = field(default_factory=list)
    docstrings_stripped: list[str] = field(default_factory=list)
    methods_compressed: list[str] = field(default_factory=list)
    pruned_files: list[str] = field(default_factory=list)
    is_within_budget: bool = True

    def summary(self) -> str:
        status = (
            "[green]FITS BUDGET[/green]"
            if self.is_within_budget
            else "[bold red]OVER BUDGET[/bold red]"
        )
        return (
            f"Budget: {self.total_budget:,} tokens | Used: {self.final_tokens:,} "
            f"({self.utilization_pct:.1f}%) | Status: {status}"
        )


class BudgetOptimizer:
    """Dynamically adapts file inclusion modes to strictly honor a token budget."""

    @classmethod
    def optimize(
        cls,
        files: list[CollectedFile],
        budget_tokens: int,
    ) -> tuple[list[CollectedFile], BudgetReport]:
        """
        Adaptively tier and compress files so total token consumption fits budget_tokens.
        """
        initial_tokens = sum(f.token_count for f in files)
        report = BudgetReport(
            total_budget=budget_tokens,
            initial_tokens=initial_tokens,
            final_tokens=initial_tokens,
            is_within_budget=initial_tokens <= budget_tokens,
        )

        if initial_tokens <= budget_tokens:
            report.utilization_pct = (initial_tokens / budget_tokens) * 100
            return files, report

        current_files = list(files)

        # STAGE 1: Prune PERIPHERAL files completely when budget is constrained
        kept_files: list[CollectedFile] = []
        for f in current_files:
            if f.role == FileRole.PERIPHERAL:
                report.pruned_files.append(f.relative_path)
            else:
                kept_files.append(f)

        current_files = kept_files if kept_files else current_files
        curr_tokens = sum(f.token_count for f in current_files)
        if curr_tokens <= budget_tokens:
            return cls._finalize_report(current_files, report, curr_tokens)

        # STAGE 2: Downgrade DEPENDENCY_CONTRACT files to AST Skeletons
        for f in current_files:
            if (
                f.role == FileRole.DEPENDENCY_CONTRACT
                and f.mode == "full"
                and ASTParser.can_parse(f.relative_path)
            ):
                f.content = ASTParser.extract_skeleton(f.content, f.relative_path)
                f.mode = "skeleton"
                f.token_count = Analyzer.estimate_tokens(f.content)
                f.line_count = len(f.content.splitlines())
                f.byte_size = len(f.content.encode("utf-8"))
                report.downgraded_to_skeleton.append(f.relative_path)

        curr_tokens = sum(f.token_count for f in current_files)
        if curr_tokens <= budget_tokens:
            return cls._finalize_report(current_files, report, curr_tokens)

        # STAGE 3: Clean AST docstring stripping on DEPENDENCY_CONTRACT files
        for f in current_files:
            if f.role == FileRole.DEPENDENCY_CONTRACT and f.relative_path.endswith(".py"):
                stripped = ASTParser.strip_docstrings_python(f.content)
                if len(stripped) < len(f.content):
                    f.content = stripped
                    f.mode = "compact_contract"
                    f.token_count = Analyzer.estimate_tokens(f.content)
                    f.line_count = len(f.content.splitlines())
                    f.byte_size = len(f.content.encode("utf-8"))
                    report.docstrings_stripped.append(f.relative_path)

        curr_tokens = sum(f.token_count for f in current_files)
        if curr_tokens <= budget_tokens:
            return cls._finalize_report(current_files, report, curr_tokens)

        # STAGE 4: Intelligently compress large internal method bodies in FOCUS_TARGET files
        for f in current_files:
            if f.role == FileRole.FOCUS_TARGET and f.relative_path.endswith(".py"):
                compressed = ASTParser.compress_large_methods_python(f.content, min_lines=15)
                if len(compressed) < len(f.content):
                    f.content = compressed
                    f.mode = "compressed_target"
                    f.token_count = Analyzer.estimate_tokens(f.content)
                    f.line_count = len(f.content.splitlines())
                    f.byte_size = len(f.content.encode("utf-8"))
                    report.methods_compressed.append(f.relative_path)

        curr_tokens = sum(f.token_count for f in current_files)
        if curr_tokens <= budget_tokens:
            return cls._finalize_report(current_files, report, curr_tokens)

        # STAGE 5: If still over budget, aggressively compress all non-focus methods to 0 bodies
        for f in current_files:
            if f.role != FileRole.FOCUS_TARGET and ASTParser.can_parse(f.relative_path):
                f.content = ASTParser.extract_skeleton(f.content, f.relative_path)
                f.content = ASTParser.strip_docstrings_python(f.content)
                f.token_count = Analyzer.estimate_tokens(f.content)

        curr_tokens = sum(f.token_count for f in current_files)
        return cls._finalize_report(current_files, report, curr_tokens)

    @classmethod
    def _finalize_report(
        cls,
        files: list[CollectedFile],
        report: BudgetReport,
        final_tokens: int,
    ) -> tuple[list[CollectedFile], BudgetReport]:
        report.final_tokens = final_tokens
        report.is_within_budget = final_tokens <= report.total_budget
        report.utilization_pct = (
            (final_tokens / report.total_budget) * 100 if report.total_budget else 0.0
        )
        return files, report
