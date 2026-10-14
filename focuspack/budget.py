"""
Adaptive token budgeting engine for focuspack.
Unlike static dumpers that merely fail CI, focuspack dynamically tiers and
optimizes context content to fit strictly within a model's context window.
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
    pruned_files: list[str] = field(default_factory=list)
    is_within_budget: bool = True

    def summary(self) -> str:
        status = (
            "[green]FITS BUDGET[/green]"
            if self.is_within_budget
            else "[yellow]OVER BUDGET[/yellow]"
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
        Adaptively tier files so total token consumption <= budget_tokens.
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

        # STAGE 1: Downgrade PERIPHERAL files from FULL to SKELETON
        for f in current_files:
            if (
                f.role == FileRole.PERIPHERAL
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

        # STAGE 2: Downgrade DEPENDENCY_CONTRACT files to SKELETON
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

        # STAGE 3: Prune PERIPHERAL files completely (they remain in the directory structure map)
        kept_files: list[CollectedFile] = []
        for f in current_files:
            if f.role == FileRole.PERIPHERAL:
                report.pruned_files.append(f.relative_path)
            else:
                kept_files.append(f)

        current_files = kept_files
        curr_tokens = sum(f.token_count for f in current_files)
        if curr_tokens <= budget_tokens:
            return cls._finalize_report(current_files, report, curr_tokens)

        # STAGE 4: Downgrade non-focus files to compact signatures (strip docstrings from contracts)
        for f in current_files:
            if f.role != FileRole.FOCUS_TARGET and ASTParser.can_parse(f.relative_path):
                compact_lines = [
                    line
                    for line in f.content.splitlines()
                    if not line.strip().startswith('"""') and not line.strip().startswith("'''")
                ]
                f.content = "\n".join(compact_lines)
                f.mode = "compact_contract"
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
