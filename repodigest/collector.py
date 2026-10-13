"""
File discovery, filtering, and content collection module for repodigest.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from repodigest.analyzer import Analyzer
from repodigest.ast_parser import ASTParser
from repodigest.config import (
    BINARY_EXTENSIONS,
    DEFAULT_IGNORE_PATTERNS,
    RepoDigestConfig,
)
from repodigest.security import Finding, SecurityScanner

# Check for pathspec library
try:
    import pathspec

    _HAS_PATHSPEC = True
except ImportError:
    _HAS_PATHSPEC = False


@dataclass
class CollectedFile:
    """Represents a packaged source file."""

    relative_path: str
    absolute_path: Path
    extension: str
    content: str
    line_count: int
    byte_size: int
    token_count: int
    mode: str
    secrets_redacted: int


class Collector:
    """Discovers, filters, and loads repository files."""

    def __init__(self, config: RepoDigestConfig | None = None):
        self.config = config or RepoDigestConfig()
        self.root_path = Path(self.config.root_path).resolve()
        self.scanner = SecurityScanner()
        self.findings: list[Finding] = []
        self._ignore_spec = self._build_ignore_spec()

    def _build_ignore_spec(self):
        """Construct ignore pattern matcher combining defaults, gitignore, and user patterns."""
        patterns = list(DEFAULT_IGNORE_PATTERNS)
        patterns.extend(self.config.exclude_patterns)

        # Read root .gitignore if enabled
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
        norm_path = relative_path_str.replace("\\", "/")
        if is_dir and not norm_path.endswith("/"):
            norm_path += "/"

        if _HAS_PATHSPEC:
            return self._ignore_spec.match_file(norm_path)

        # Basic fallback matcher if pathspec is not installed
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
                # Attempt to decode chunk as utf-8
                chunk.decode("utf-8")
        except UnicodeDecodeError:
            return True
        except Exception:
            return True
        return False

    def matches_includes(self, relative_path_str: str) -> bool:
        """Check if file matches include filters (if any specified)."""
        if not self.config.include_patterns:
            return True

        norm_path = relative_path_str.replace("\\", "/")
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
                    if " -> " in raw_file:  # Renamed file
                        raw_file = raw_file.split(" -> ")[1].strip()
                    files.add(raw_file.replace("\\", "/"))
            return files
        except Exception:
            return None

    def collect(self, git_diff_only: bool = False) -> list[CollectedFile]:
        """Scan directory and collect matching source files."""
        collected: list[CollectedFile] = []
        self.findings.clear()

        filter_files = None
        if git_diff_only:
            filter_files = self.get_git_modified_files()

        for dirpath, dirnames, filenames in os.walk(self.root_path):
            current_dir = Path(dirpath)
            rel_dir = current_dir.relative_to(self.root_path).as_posix()

            # Prune ignored directories in-place
            dirnames[:] = [
                d
                for d in dirnames
                if not self.is_ignored(f"{rel_dir}/{d}" if rel_dir != "." else d, is_dir=True)
            ]

            for fname in filenames:
                file_path = current_dir / fname
                rel_path = file_path.relative_to(self.root_path).as_posix()

                if filter_files is not None and rel_path not in filter_files:
                    continue

                if self.is_ignored(rel_path, is_dir=False):
                    continue

                if not self.matches_includes(rel_path):
                    continue

                if self.is_binary_file(file_path):
                    continue

                try:
                    file_size = file_path.stat().st_size
                except OSError:
                    continue

                if file_size > self.config.max_file_size_bytes:
                    continue

                try:
                    with open(file_path, encoding="utf-8", errors="replace") as f:
                        raw_text = f.read()
                except Exception:
                    continue

                # Secret scanning
                scanned_findings = self.scanner.scan_text(raw_text, rel_path)
                self.findings.extend(scanned_findings)

                secrets_count = 0
                processed_content = raw_text
                if self.config.redact_secrets and scanned_findings:
                    processed_content, secrets_count = self.scanner.redact_text(raw_text)

                # Determine mode (full vs skeleton)
                mode_used = "full"
                if self.config.mode == "skeleton" and ASTParser.can_parse(rel_path):
                    processed_content = ASTParser.extract_skeleton(processed_content, rel_path)
                    mode_used = "skeleton"
                elif self.config.mode == "auto" and ASTParser.can_parse(rel_path):
                    # In auto mode, compress large files (> 300 lines or > 12 KB)
                    line_count = len(raw_text.splitlines())
                    if line_count > 300 or file_size > 12 * 1024:
                        processed_content = ASTParser.extract_skeleton(processed_content, rel_path)
                        mode_used = "skeleton"

                lines = len(processed_content.splitlines())
                byte_size = len(processed_content.encode("utf-8"))
                tokens = Analyzer.estimate_tokens(processed_content)

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
                        secrets_redacted=secrets_count,
                    )
                )

        # Sort files alphabetically for deterministic output
        collected.sort(key=lambda x: x.relative_path)
        return collected

    def build_file_tree(self, files: list[CollectedFile]) -> str:
        """Generate a clean ASCII tree representation of collected files."""
        if not files:
            return "(No files found)\n"

        tree: dict = {}
        for f in files:
            parts = f.relative_path.split("/")
            curr = tree
            for part in parts[:-1]:
                curr = curr.setdefault(part, {})
            curr[parts[-1]] = None

        lines = [f"{self.root_path.name}/"]

        def render_sub_tree(node: dict, prefix: str = ""):
            items = sorted(node.keys(), key=lambda k: (node[k] is None, k))
            for i, name in enumerate(items):
                is_last = i == len(items) - 1
                connector = "└── " if is_last else "├── "
                sub_prefix = "    " if is_last else "│   "

                if node[name] is None:
                    lines.append(f"{prefix}{connector}{name}")
                else:
                    lines.append(f"{prefix}{connector}{name}/")
                    render_sub_tree(node[name], prefix + sub_prefix)

        render_sub_tree(tree)
        return "\n".join(lines)
