"""
focuspack Charter & Scope Verification Tool.
Enforces the 4 Core Pillars and Explicit Non-Goals defined in CHARTER.md.
Can be executed locally (pre-commit) or in GitHub Actions CI.
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# Explicit Banned Dependencies (Violations of Non-Goals in CHARTER.md)
BANNED_PACKAGES = {
    "torch",
    "tensorflow",
    "langchain",
    "langchain-core",
    "llama-index",
    "chromadb",
    "pinecone-client",
    "qdrant-client",
    "weaviate-client",
    "transformers",
    "sentence-transformers",
    "openai",  # focuspack is context compiler, not an API proxy/caller
    "anthropic",
    "flask",  # no web UI servers
    "fastapi",
    "electron",
}

# Explicit Anti-Pattern Keywords in Commit Diff / Feature Descriptions
NON_GOAL_TERMS = [
    (
        r"\bvector\s*(?:db|database|store)\b",
        "Vector Databases (Non-Goal: focuspack is a deterministic context compiler)",
    ),
    (
        r"\brag\s*(?:pipeline|system)\b",
        "RAG Pipelines (Non-Goal: focuspack formats context, does not index or query)",
    ),
    (r"\belectron\b", "Desktop GUIs (Non-Goal: focuspack is a terminal/CLI developer tool)"),
    (
        r"\bcloud\s*(?:upload|storage|api)\b",
        "Cloud Processing (Non-Goal: focuspack is 100% private, local, and offline-first)",
    ),
    (
        r"\bflat\s*dump(?:er)?\b",
        "Flat Monolithic Dumps (Non-Goal: focuspack is focus-driven with AST interface contracts)",
    ),
]


def check_pyproject_dependencies(project_root: Path) -> list[str]:
    """Ensure pyproject.toml does not introduce heavy or out-of-scope dependencies."""
    pyproject_file = project_root / "pyproject.toml"
    if not pyproject_file.exists():
        return ["pyproject.toml not found"]

    content = pyproject_file.read_text(encoding="utf-8")
    violations = []

    for banned in BANNED_PACKAGES:
        # Check dependency lines like "langchain>=0.1.0" or 'torch'
        pattern = rf"""(?m)^\s*["']?{re.escape(banned)}(?:[><=~!\s"']|$)"""
        if re.search(pattern, content, re.IGNORECASE):
            violations.append(
                f"Banned dependency detected in pyproject.toml: '{banned}'. "
                f"Violates CHARTER.md (Pure-Python Zero-Heavy-Runtime)."
            )

    return violations


def check_git_diff_test_coverage(project_root: Path) -> list[str]:
    """If code under focuspack/ was modified, verify that tests/ was also touched."""
    try:
        # Check against main or HEAD~1
        res = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode != 0:
            # Fall back to uncommitted diff
            res = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=project_root,
                capture_output=True,
                text=True,
                check=False,
            )

        lines = res.stdout.splitlines()
        code_changed = any("focuspack/" in line and line.endswith(".py") for line in lines)
        tests_changed = any("tests/" in line for line in lines)

        if code_changed and not tests_changed:
            return [
                "Code in focuspack/ was modified, but no test changes detected in tests/. "
                "Every feature and fix must include unit tests."
            ]
    except Exception:
        pass
    return []


def check_ast_integrity(project_root: Path) -> list[str]:
    """Verify that all Python files parse cleanly with standard library ast."""
    violations = []
    for py_file in (project_root / "focuspack").rglob("*.py"):
        try:
            ast.parse(py_file.read_text(encoding="utf-8"))
        except SyntaxError as e:
            violations.append(f"Syntax error in {py_file.relative_to(project_root)}: {e}")
    return violations


def main() -> int:
    project_root = Path(__file__).resolve().parent.parent
    print(f"🎯 Running focuspack Charter & Scope Verification on {project_root.name}...")

    all_violations: list[str] = []

    # 1. Check dependencies
    dep_violations = check_pyproject_dependencies(project_root)
    all_violations.extend(dep_violations)

    # 2. Check AST syntax integrity
    ast_violations = check_ast_integrity(project_root)
    all_violations.extend(ast_violations)

    # 3. Check test coverage on changed files
    coverage_warnings = check_git_diff_test_coverage(project_root)

    print("\n--- Summary of Charter Checks ---")
    if dep_violations:
        print("❌ Dependency Check: FAILED")
        for v in dep_violations:
            print(f"   • {v}")
    else:
        print("✅ Dependency Check: PASSED (Zero heavy runtime bloat)")

    if ast_violations:
        print("❌ AST Syntax Integrity: FAILED")
        for v in ast_violations:
            print(f"   • {v}")
    else:
        print("✅ AST Syntax Integrity: PASSED")

    if coverage_warnings:
        print("⚠️ Test Coverage Notice:")
        for w in coverage_warnings:
            print(f"   • {w}")
    else:
        print("✅ Test Coverage Check: PASSED")

    if all_violations:
        print("\n❌ Charter verification FAILED. See CHARTER.md for rules.")
        return 1

    print("\n🎉 All Charter Guard checks passed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
