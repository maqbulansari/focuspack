"""
Dependency graph and focus resolution engine for focuspack.
Traverses import graphs using Python AST to link focus targets with their
contract dependencies, supporting submodules, relative imports, and src/ layouts.
"""

from __future__ import annotations

import ast
import re
import warnings
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class FileRole(str, Enum):
    """Semantic role of a file in the generated LLM context."""

    FOCUS_TARGET = "focus_target"  # The primary file(s) being worked on
    DEPENDENCY_CONTRACT = "dependency_contract"  # Directly imported interface contract
    PERIPHERAL = "peripheral"  # Other files in the project


@dataclass
class NodeMetadata:
    """Graph node representing a source file."""

    relative_path: str
    absolute_path: Path
    role: FileRole = FileRole.PERIPHERAL
    imports: set[str] = field(default_factory=set)  # Relative paths of files this node imports
    imported_by: set[str] = field(default_factory=set)  # Files that import this node
    depth: int = 999


def clean_relative_path(path_str: str) -> str:
    """Normalize path separators and safely strip leading './' without touching leading dots."""
    p = path_str.replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p


class DependencyGraph:
    """Builds and queries the repository's import dependency graph."""

    def __init__(self, root_path: Path):
        self.root_path = root_path.resolve()
        self.nodes: dict[str, NodeMetadata] = {}
        self._package_roots: list[str] = ["", "src"]

    def add_file(self, relative_path: str, absolute_path: Path):
        """Register a file node into the graph."""
        norm_path = clean_relative_path(relative_path)
        if norm_path not in self.nodes:
            self.nodes[norm_path] = NodeMetadata(
                relative_path=norm_path,
                absolute_path=absolute_path,
            )
            # Detect package roots like src/ or custom dirs
            parts = norm_path.split("/")
            if (
                len(parts) > 1
                and parts[0] not in self._package_roots
                and parts[0] not in {".", "tests", "docs"}
            ):
                self._package_roots.append(parts[0])

    def build_graph(self):
        """Parse all registered files to extract imports and link dependencies."""
        for rel_path, node in self.nodes.items():
            if node.absolute_path.suffix.lower() == ".py":
                self._parse_python_imports(rel_path, node)
            elif node.absolute_path.suffix.lower() in {".ts", ".tsx", ".js", ".jsx"}:
                self._parse_js_ts_imports(rel_path, node)

    def _match_candidate(self, candidate_path: str) -> str | None:
        """Check if candidate path exists in registered nodes."""
        clean = clean_relative_path(candidate_path)
        if clean in self.nodes:
            return clean
        for ext in [".py", "/__init__.py"]:
            with_ext = f"{clean}{ext}"
            if with_ext in self.nodes:
                return with_ext
        return None

    def _resolve_python_import(
        self,
        current_rel_path: str,
        module_name: str | None,
        alias_name: str | None = None,
        level: int = 0,
    ) -> list[str]:
        """
        Resolve Python import statement to registered file path(s).
        Handles:
          - from . import models
          - from app.core import store
          - from app import cyc_b
          - import requests.models
        """
        resolved: list[str] = []
        curr_dir = Path(current_rel_path).parent

        # 1. Relative Import (level > 0)
        if level > 0:
            target_dir = curr_dir
            for _ in range(level - 1):
                target_dir = target_dir.parent

            base_dir_posix = target_dir.as_posix()
            if base_dir_posix == ".":
                base_dir_posix = ""

            candidates: list[str] = []
            if module_name:
                mod_sub = module_name.replace(".", "/")
                prefix = f"{base_dir_posix}/{mod_sub}" if base_dir_posix else mod_sub
                # Check submodule with alias e.g. from .pkg import submod
                if alias_name:
                    candidates.append(f"{prefix}/{alias_name}")
                candidates.append(prefix)
            else:
                # from . import models
                if alias_name:
                    prefix = f"{base_dir_posix}/{alias_name}" if base_dir_posix else alias_name
                    candidates.append(prefix)
                if base_dir_posix:
                    candidates.append(base_dir_posix)

            for cand in candidates:
                matched = self._match_candidate(cand)
                if matched and matched not in resolved:
                    resolved.append(matched)

            return resolved

        # 2. Absolute Import (level == 0)
        # Check against all detected package roots (e.g. root, src/, etc.)
        search_roots = ["", "src"]
        curr_dir_str = curr_dir.as_posix()
        if curr_dir_str and curr_dir_str not in search_roots:
            search_roots.append(curr_dir_str)

        candidates = []
        if module_name:
            mod_sub = module_name.replace(".", "/")
            # Submodule via alias: from app.core import store -> app/core/store.py
            if alias_name:
                candidates.append(f"{mod_sub}/{alias_name}")
            candidates.append(mod_sub)
        elif alias_name:
            candidates.append(alias_name)

        for root in search_roots:
            for cand in candidates:
                full_cand = f"{root}/{cand}" if root else cand
                matched = self._match_candidate(full_cand)
                if matched and matched not in resolved:
                    resolved.append(matched)

        return resolved

    def _parse_python_imports(self, rel_path: str, node: NodeMetadata):
        """Extract imports from Python AST."""
        try:
            with open(node.absolute_path, encoding="utf-8", errors="replace") as f:
                code = f.read()
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=SyntaxWarning)
                tree = ast.parse(code)
        except Exception:
            return

        for ast_node in ast.walk(tree):
            if isinstance(ast_node, ast.Import):
                for alias in ast_node.names:
                    # e.g. import requests.sessions
                    for target in self._resolve_python_import(rel_path, alias.name, level=0):
                        if target != rel_path:
                            node.imports.add(target)
            elif isinstance(ast_node, ast.ImportFrom):
                # e.g. from . import models or from requests.models import Request
                for alias in ast_node.names:
                    targets = self._resolve_python_import(
                        rel_path, ast_node.module, alias_name=alias.name, level=ast_node.level
                    )
                    for target in targets:
                        if target != rel_path:
                            node.imports.add(target)

        for dep in node.imports:
            if dep in self.nodes:
                self.nodes[dep].imported_by.add(rel_path)

    def _parse_js_ts_imports(self, rel_path: str, node: NodeMetadata):
        """Extract relative imports from JS/TS code."""
        try:
            with open(node.absolute_path, encoding="utf-8", errors="replace") as f:
                code = f.read()
        except Exception:
            return

        curr_dir = Path(rel_path).parent
        import_regex = re.compile(
            r"""(?:import\s+.*?from\s+['"]|require\(['"])([\.\/][^'"]+)['"]"""
        )
        for match in import_regex.finditer(code):
            raw_path = match.group(1)
            resolved_base = clean_relative_path((curr_dir / raw_path).as_posix())
            matched = self._match_candidate(resolved_base)
            if matched and matched != rel_path:
                node.imports.add(matched)
                if matched in self.nodes:
                    self.nodes[matched].imported_by.add(rel_path)

    def apply_focus(self, focus_targets: list[str], max_depth: int = 1) -> dict[str, FileRole]:
        """
        Given focus targets (files or directories), assign semantic roles across the repository.
        Cycle-safe BFS traversal up to max_depth.
        """
        roles: dict[str, FileRole] = {p: FileRole.PERIPHERAL for p in self.nodes}
        for node in self.nodes.values():
            node.role = FileRole.PERIPHERAL
            node.depth = 999

        focus_set: set[str] = set()
        for target in focus_targets:
            target_norm = clean_relative_path(target).rstrip("/")
            for p in self.nodes:
                if p == target_norm or p.startswith(f"{target_norm}/"):
                    focus_set.add(p)
                    roles[p] = FileRole.FOCUS_TARGET
                    self.nodes[p].role = FileRole.FOCUS_TARGET
                    self.nodes[p].depth = 0

        # Cycle-safe BFS traversal
        current_frontier = set(focus_set)
        visited = set(focus_set)

        for d in range(1, max_depth + 1):
            next_frontier = set()
            for p in current_frontier:
                if p in self.nodes:
                    for dep in self.nodes[p].imports:
                        if dep not in visited:
                            visited.add(dep)
                            if roles.get(dep) != FileRole.FOCUS_TARGET:
                                roles[dep] = FileRole.DEPENDENCY_CONTRACT
                                self.nodes[dep].role = FileRole.DEPENDENCY_CONTRACT
                                self.nodes[dep].depth = d
                                next_frontier.add(dep)
            current_frontier = next_frontier

        return roles
