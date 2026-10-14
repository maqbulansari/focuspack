"""
File discovery, filtering, dependency linking, and content collection for focuspack.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from focuspack.analyzer import Analyzer
from focuspack.ast_parser import ASTParser
from focuspack.budget import BudgetOptimizer, BudgetReport
from focuspack.config import (
    BINARY_EXTENSIONS,
    DEFAULT_IGNORE_PATTERNS,
    FocusPackConfig,
)
from focuspack.graph import DependencyGraph, FileRole
from focuspack.security import Finding, SecurityScanner

try:
    import pathspec

    _HAS_PATHSPEC = True
except ImportError:
    _HAS_PATHSPEC = False


@dataclass
class CollectedFile:
    """Represents a packaged source file with semantic context."""

    relative_path: str
    absolute_path: Path
    extension: str
    content: str
    line_count: int
    byte_size: int
    token_count: int
    mode: str  # "full", "skeleton", "compact_contract", "compressed_target"
    role: FileRole = FileRole.PERIPHERAL
    secrets_redacted: int = 0
    imports: list[str] = field(default_factory=list)
    imported_by: list[str] = field(default_factory=list)
    depth: int = 0


def clean_relative_path(path_str: str) -> str:
    """Normalize path separators and safely strip leading './' without touching leading dots."""
    p = path_str.replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p


class Collector:
    """Discovers files, tracks dependencies, applies focus, and optimizes budgets."""

    def __init__(self, config: FocusPackConfig | None = None):
        self.config = config or FocusPackConfig()
        self.root_path = Path(self.config.root_path).resolve()
        self.scanner = SecurityScanner()
        self.findings: list[Finding] = []
        self._ignore_spec = self._build_ignore_spec()
        self.graph = DependencyGraph(self.root_path)
        self.budget_report: BudgetReport | None = None

    def _build_ignore_spec(self):
        """Construct ignore pattern matcher combining defaults, gitignore, and user patterns."""
        patterns = list(DEFAULT_IGNORE_PATTERNS)
        patterns.extend(self.config.exclude_patterns)

        if self.config.respect_gitignore:
            gitignore_path = self.root_path / ".gitignore"
            if gitignore_path.is_file():
                try:
                    with open(gitignore_path, encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            stripped = line.strip()
                            if stripped and not stripped.startswith("#"):
                                patterns.append(stripped)
                except Exception:
                    pass

        if _HAS_PATHSPEC:
            try:
                return pathspec.PathSpec.from_lines("gitignore", patterns)
            except Exception:
                return pathspec.PathSpec.from_lines("gitwildmatch", patterns)
        return patterns

    def is_ignored(self, relative_path_str: str, is_dir: bool = False) -> bool:
        """Check if a path matches ignore patterns."""
        norm_path = clean_relative_path(relative_path_str)
        if is_dir and not norm_path.endswith("/"):
            norm_path += "/"

        if _HAS_PATHSPEC:
            return self._ignore_spec.match_file(norm_path)

        for pat in self._ignore_spec:
            clean_pat = pat.rstrip("/")
            if pat.endswith("/"):
                if f"/{clean_pat}/" in f"/{norm_path}" or norm_path.startswith(f"{clean_pat}/"):
                    return True
            else:
                if (
                    norm_path == clean_pat
                    or norm_path.endswith(f"/{clean_pat}")
                    or Path(norm_path).match(pat)
                ):
                    return True
        return False

    def is_binary_file(self, file_path: Path) -> bool:
        """Detect whether a file is binary by extension and byte inspection."""
        if file_path.suffix.lower() in BINARY_EXTENSIONS:
            return True

        try:
            with open(file_path, "rb") as f:
                chunk = f.read(1024)
                if b"\x00" in chunk:
                    return True
                chunk.decode("utf-8")
        except Exception:
            return True
        return False

    def matches_includes(self, relative_path_str: str) -> bool:
        """Check if file matches include filters."""
        if not self.config.include_patterns:
            return True

        norm_path = clean_relative_path(relative_path_str)
        for pat in self.config.include_patterns:
            if Path(norm_path).match(pat) or pat in norm_path:
                return True
        return False

    def get_git_modified_files(self) -> set[str] | None:
        """Retrieve list of modified and untracked files from git status."""
        try:
            res = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.root_path,
                capture_output=True,
                text=True,
                check=True,
            )
            files = set()
            for line in res.stdout.splitlines():
                if len(line) >= 4:
                    raw_file = line[3:].strip()
                    if " -> " in raw_file:
                        raw_file = raw_file.split(" -> ")[1].strip()
                    files.add(clean_relative_path(raw_file))
            return files
        except Exception:
            return None

    def validate_focus_targets(self, targets: list[str]):
        """Ensure all requested focus targets match at least one file in the repository."""
        for target in targets:
            clean = clean_relative_path(target).rstrip("/")
            target_path = Path(target)
            rel_from_root = None
            if target_path.is_absolute():
                try:
                    rel_from_root = clean_relative_path(
                        target_path.resolve().relative_to(self.root_path).as_posix()
                    )
                except ValueError:
                    pass
            else:
                try:
                    resolved_cwd = (Path.cwd() / target).resolve()
                    rel_from_root = clean_relative_path(
                        resolved_cwd.relative_to(self.root_path).as_posix()
                    )
                except ValueError:
                    pass

            candidates = {clean}
            if rel_from_root:
                candidates.add(rel_from_root)

            matched = any(
                any(
                    p == c or p.startswith(f"{c}/") or p.endswith(f"/{c}") or c in p
                    for c in candidates
                )
                for p in self.graph.nodes
            )
            if not matched:
                raise FileNotFoundError(
                    f"Focus target '{target}' does not match any file or directory in the repository."
                )

    def collect(self, git_diff_only: bool = False) -> list[CollectedFile]:
        """Scan directory, build dependency graph, apply focus roles, and enforce budget."""
        collected: list[CollectedFile] = []
        self.findings.clear()

        filter_files = None
        if git_diff_only:
            filter_files = self.get_git_modified_files()

        # Step 1: Discover valid files and register nodes in graph
        discovered_paths: list[tuple[str, Path]] = []
        for dirpath, dirnames, filenames in os.walk(self.root_path):
            current_dir = Path(dirpath)
            rel_dir = current_dir.relative_to(self.root_path).as_posix()
            if rel_dir == ".":
                rel_dir = ""

            dirnames[:] = [
                d
                for d in dirnames
                if not self.is_ignored(f"{rel_dir}/{d}" if rel_dir else d, is_dir=True)
            ]

            for fname in filenames:
                file_path = current_dir / fname
                rel_path = file_path.relative_to(self.root_path).as_posix()

                if filter_files is not None and rel_path not in filter_files:
                    continue

                if self.is_ignored(rel_path, is_dir=False) or not self.matches_includes(rel_path):
                    continue

                if self.is_binary_file(file_path):
                    continue

                try:
                    if file_path.stat().st_size > self.config.max_file_size_bytes:
                        continue
                except OSError:
                    continue

                discovered_paths.append((rel_path, file_path))
                self.graph.add_file(rel_path, file_path)

        # Step 2: Build dependency linkages
        self.graph.build_graph()

        # Step 3: Apply focus resolution
        active_focus = list(self.config.focus_targets)
        if git_diff_only and filter_files:
            active_focus.extend(filter_files)

        if active_focus:
            self.validate_focus_targets(active_focus)
            roles_map = self.graph.apply_focus(active_focus, max_depth=self.config.focus_depth)
        else:
            roles_map = {}

        # Step 4: Load and process content
        for rel_path, file_path in discovered_paths:
            role = roles_map.get(rel_path, FileRole.PERIPHERAL)

            # CRITICAL FIX: When focus targets are specified, exclude peripheral files
            # (unrelated modules, README, LICENSE, CI files) from content payload by default!
            if active_focus and role == FileRole.PERIPHERAL and not self.config.include_peripherals:
                continue

            try:
                with open(file_path, encoding="utf-8", errors="replace") as f:
                    raw_text = f.read()
            except Exception:
                continue

            # Secret scanning & redaction
            scanned_findings = self.scanner.scan_text(raw_text, rel_path)
            self.findings.extend(scanned_findings)

            secrets_count = 0
            processed_content = raw_text
            if self.config.redact_secrets and scanned_findings:
                processed_content, secrets_count = self.scanner.redact_text(raw_text)

            # Determine mode based on role & config
            mode_used = "full"
            if self.config.mode == "skeleton" and ASTParser.can_parse(rel_path):
                processed_content = ASTParser.extract_skeleton(processed_content, rel_path)
                mode_used = "skeleton"
            elif self.config.mode == "auto":
                if active_focus:
                    # Focus targets are FULL; direct contracts are SKELETON
                    if role == FileRole.DEPENDENCY_CONTRACT and ASTParser.can_parse(rel_path):
                        processed_content = ASTParser.extract_skeleton(processed_content, rel_path)
                        mode_used = "skeleton"
                    elif role == FileRole.PERIPHERAL and ASTParser.can_parse(rel_path):
                        processed_content = ASTParser.extract_skeleton(processed_content, rel_path)
                        mode_used = "skeleton"
                else:
                    # Generic auto mode: compress huge files > 300 lines
                    if len(raw_text.splitlines()) > 300 and ASTParser.can_parse(rel_path):
                        processed_content = ASTParser.extract_skeleton(processed_content, rel_path)
                        mode_used = "skeleton"

            lines = len(processed_content.splitlines())
            byte_size = len(processed_content.encode("utf-8"))
            tokens = Analyzer.estimate_tokens(processed_content)

            node = self.graph.nodes.get(rel_path)
            imports_list = sorted(node.imports) if node else []
            imported_by_list = sorted(node.imported_by) if node else []
            depth_val = node.depth if node else 0

            collected.append(
                CollectedFile(
                    relative_path=rel_path,
                    absolute_path=file_path,
                    extension=file_path.suffix.lower(),
                    content=processed_content,
                    line_count=lines,
                    byte_size=byte_size,
                    token_count=tokens,
                    mode=mode_used,
                    role=role,
                    secrets_redacted=secrets_count,
                    imports=imports_list,
                    imported_by=imported_by_list,
                    depth=depth_val,
                )
            )

        # Prioritize files: Focus Targets first, then Contracts, then Peripherals
        collected.sort(
            key=lambda x: (
                0
                if x.role == FileRole.FOCUS_TARGET
                else (1 if x.role == FileRole.DEPENDENCY_CONTRACT else 2),
                x.relative_path,
            )
        )

        # Step 5: Adaptive Token Budgeting
        if self.config.token_budget and self.config.token_budget > 0:
            from focuspack.formatter import Formatter

            def measure_renderer(
                file_list: list[CollectedFile], rep: BudgetReport | None = None
            ) -> str:
                s = Analyzer.compute_stats(file_list)
                tree_str = self.build_file_tree(file_list)
                return Formatter.format_all(
                    files=file_list,
                    stats=s,
                    file_tree=tree_str,
                    fmt=self.config.output_format,
                    include_tree=self.config.include_tree,
                    budget_report=rep,
                    task_prompt=self.config.task_template,
                )

            collected, self.budget_report = BudgetOptimizer.optimize(
                collected, self.config.token_budget, renderer=measure_renderer
            )

        return collected

    def build_file_tree(self, files: list[CollectedFile]) -> str:
        """Generate clean ASCII tree representation with semantic role markers."""
        # Use graph nodes so the full architecture is visible even if peripheral contents are pruned
        if not self.graph.nodes:
            return "(No files found)\n"

        file_roles = {f.relative_path: f.role for f in files}

        tree: dict = {}
        for rel_path in self.graph.nodes:
            parts = rel_path.split("/")
            curr = tree
            for part in parts[:-1]:
                curr = curr.setdefault(part, {})
            curr[parts[-1]] = rel_path

        lines = [f"{self.root_path.name}/"]

        def render_sub_tree(node: dict, prefix: str = ""):
            items = sorted(node.keys(), key=lambda k: (isinstance(node[k], dict), k))
            for i, name in enumerate(items):
                is_last = i == len(items) - 1
                connector = "└── " if is_last else "├── "
                sub_prefix = "    " if is_last else "│   "

                val = node[name]
                if isinstance(val, dict):
                    lines.append(f"{prefix}{connector}{name}/")
                    render_sub_tree(val, prefix + sub_prefix)
                else:
                    role = file_roles.get(val, FileRole.PERIPHERAL)
                    tag = ""
                    if role == FileRole.FOCUS_TARGET:
                        tag = "  [FOCUS]"
                    elif role == FileRole.DEPENDENCY_CONTRACT:
                        tag = "  [CONTRACT]"
                    lines.append(f"{prefix}{connector}{name}{tag}")

        render_sub_tree(tree)
        return "\n".join(lines)
