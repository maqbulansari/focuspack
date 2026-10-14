"""
Dependency graph and focus resolution engine for focuspack.
Traverses import graphs using Python AST to separate active focus targets from
contract dependencies and peripheral code.
"""

from __future__ import annotations

import ast
import re
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


class DependencyGraph:
    """Builds and queries the repository's import dependency graph."""

    def __init__(self, root_path: Path):
        self.root_path = root_path.resolve()
        self.nodes: dict[str, NodeMetadata] = {}

    def add_file(self, relative_path: str, absolute_path: Path):
        """Register a file node into the graph."""
        norm_path = relative_path.replace("\\", "/")
        if norm_path not in self.nodes:
            self.nodes[norm_path] = NodeMetadata(
                relative_path=norm_path,
                absolute_path=absolute_path,
            )

    def build_graph(self):
        """Parse all registered files to extract imports and link dependencies."""
        for rel_path, node in self.nodes.items():
            if node.absolute_path.suffix.lower() == ".py":
                self._parse_python_imports(rel_path, node)
            elif node.absolute_path.suffix.lower() in {".ts", ".tsx", ".js", ".jsx"}:
                self._parse_js_ts_imports(rel_path, node)

    def _resolve_python_module(
        self, current_rel_path: str, module_name: str | None, level: int = 0
    ) -> str | None:
        """Resolve a Python import to a registered file path in the repository."""
        curr_dir = Path(current_rel_path).parent

        # 1. Handle relative import (level > 0)
        if level > 0:
            target_dir = curr_dir
            for _ in range(level - 1):
                target_dir = target_dir.parent

            if module_name:
                mod_rel = (target_dir / module_name.replace(".", "/")).as_posix()
            else:
                mod_rel = target_dir.as_posix()

            for candidate in [f"{mod_rel}.py", f"{mod_rel}/__init__.py"]:
                clean = candidate.lstrip("./").replace("//", "/")
                if clean in self.nodes:
                    return clean
            return None

        if not module_name:
            return None

        # 2. Handle absolute module imports from repository root or current dir
        mod_rel_path = module_name.replace(".", "/")
        for prefix in ["", "src/"]:
            for candidate in [
                f"{prefix}{mod_rel_path}.py",
                f"{prefix}{mod_rel_path}/__init__.py",
                (curr_dir / f"{mod_rel_path}.py").as_posix(),
                (curr_dir / f"{mod_rel_path}/__init__.py").as_posix(),
            ]:
                clean = candidate.lstrip("./").replace("//", "/")
                if clean in self.nodes:
                    return clean

        return None

    def _parse_python_imports(self, rel_path: str, node: NodeMetadata):
        """Extract imports from Python AST."""
        try:
            with open(node.absolute_path, encoding="utf-8", errors="replace") as f:
                code = f.read()
            tree = ast.parse(code)
        except Exception:
            return

        for ast_node in ast.walk(tree):
            if isinstance(ast_node, ast.Import):
                for alias in ast_node.names:
                    resolved = self._resolve_python_module(rel_path, alias.name, level=0)
                    if resolved and resolved != rel_path:
                        node.imports.add(resolved)
            elif isinstance(ast_node, ast.ImportFrom):
                resolved = self._resolve_python_module(
                    rel_path, ast_node.module, level=ast_node.level
                )
                if resolved and resolved != rel_path:
                    node.imports.add(resolved)

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
        # Matches import ... from './something' or require('./something')
        import_regex = re.compile(
            r"""(?:import\s+.*?from\s+['"]|require\(['"])([\.\/][^'"]+)['"]"""
        )
        for match in import_regex.finditer(code):
            raw_path = match.group(1)
            # Resolve relative file
            resolved_base = (curr_dir / raw_path).as_posix().lstrip("./")
            for ext in ["", ".ts", ".tsx", ".js", ".jsx", "/index.ts", "/index.js"]:
                candidate = f"{resolved_base}{ext}"
                if candidate in self.nodes and candidate != rel_path:
                    node.imports.add(candidate)
                    self.nodes[candidate].imported_by.add(rel_path)
                    break

    def apply_focus(self, focus_targets: list[str], max_depth: int = 1) -> dict[str, FileRole]:
        """
        Given focus targets (files or directories), assign semantic roles across the repository.
        Returns a mapping of relative_path -> FileRole.
        """
        roles: dict[str, FileRole] = {p: FileRole.PERIPHERAL for p in self.nodes}

        # 1. Identify primary focus targets
        focus_set: set[str] = set()
        for target in focus_targets:
            target_norm = target.replace("\\", "/").rstrip("/")
            for p in self.nodes:
                if p == target_norm or p.startswith(f"{target_norm}/"):
                    focus_set.add(p)
                    roles[p] = FileRole.FOCUS_TARGET
                    self.nodes[p].role = FileRole.FOCUS_TARGET

        # 2. Traverse dependency graph outward up to max_depth
        current_frontier = set(focus_set)
        for _ in range(max_depth):
            next_frontier = set()
            for p in current_frontier:
                if p in self.nodes:
                    for dep in self.nodes[p].imports:
                        if roles.get(dep) != FileRole.FOCUS_TARGET:
                            roles[dep] = FileRole.DEPENDENCY_CONTRACT
                            self.nodes[dep].role = FileRole.DEPENDENCY_CONTRACT
                            next_frontier.add(dep)
            current_frontier = next_frontier

        return roles
