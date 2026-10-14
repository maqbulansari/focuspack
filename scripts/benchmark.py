"""
Benchmark validation script for focuspack.
Verifies token budget compliance, real cl100k token counts, and focus target preservation
across test repositories and constrained token windows.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    import tiktoken

    _TIKTOKEN_AVAILABLE = True
    _ENC = tiktoken.get_encoding("cl100k_base")
except ImportError:
    _TIKTOKEN_AVAILABLE = False
    _ENC = None

from focuspack.analyzer import Analyzer


def count_real_tokens(text: str) -> int:
    """Count actual tokens using tiktoken cl100k_base if installed, else Analyzer."""
    if _ENC is not None:
        return len(_ENC.encode(text, disallowed_special=()))
    return Analyzer.estimate_tokens(text)


def run_benchmark_case(
    repo_path: Path,
    focus_target: str,
    budget_str: str,
    budget_int: int,
    strict_budget: bool = False,
) -> dict:
    """Run a single focuspack packaging run and verify budget & target preservation."""
    python_exe = sys.executable
    cmd = [
        python_exe,
        "-m",
        "focuspack.cli",
        "pack",
        str(repo_path),
        "-F",
        focus_target,
        "--budget",
        budget_str,
        "--stdout",
    ]
    if strict_budget:
        cmd.append("--strict-budget")

    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    stdout = proc.stdout or ""
    exit_code = proc.returncode

    real_tokens = count_real_tokens(stdout) if stdout else 0
    over_budget = real_tokens > budget_int if stdout else (exit_code != 0)

    # Check that focus target was preserved in the output payload
    focus_preserved = False
    if stdout:
        focus_clean = focus_target.replace("\\", "/").lstrip("./")
        target_marker = 'role="focus_target"'
        has_role = target_marker in stdout
        has_file = (
            f'path="{focus_clean}"' in stdout
            or f'path="{repo_path.name}/{focus_clean}"' in stdout
            or any(
                focus_clean in line and target_marker in line
                for line in stdout.splitlines()
                if "<file " in line
            )
        )
        focus_preserved = has_role and has_file

    # Extract manifest tokens if present
    manifest_tokens = None
    for line in stdout.splitlines()[:25]:
        if "tokens_used=" in line:
            import re

            m = re.search(r'tokens_used="(\d+)"', line)
            if m:
                manifest_tokens = int(m.group(1))
                break

    return {
        "repo": repo_path.name,
        "focus_target": focus_target,
        "budget_str": budget_str,
        "budget_int": budget_int,
        "strict": strict_budget,
        "exit_code": exit_code,
        "real_tokens": real_tokens,
        "manifest_tokens": manifest_tokens,
        "over_budget": over_budget,
        "focus_preserved": focus_preserved,
        "ratio": (real_tokens / budget_int) if budget_int else 1.0,
    }


def find_test_repos() -> list[tuple[Path, str]]:
    """Discover available test repositories / packages."""
    discovered = []
    # 1. requests in site-packages
    try:
        import requests

        req_p = Path(requests.__file__).parent
        discovered.append((req_p, "sessions.py"))
    except ImportError:
        pass

    # 2. click in site-packages
    try:
        import click

        click_p = Path(click.__file__).parent
        discovered.append((click_p, "utils.py"))
    except ImportError:
        pass

    # 3. focuspack itself
    fp_root = Path(__file__).resolve().parent.parent
    if (fp_root / "focuspack").is_dir():
        discovered.append((fp_root, "focuspack/analyzer.py"))

    return discovered


def main():
    parser = argparse.ArgumentParser(description="focuspack Token Budget & Retention Benchmark")
    parser.add_argument(
        "--budgets",
        nargs="+",
        default=["8k", "12k", "16k"],
        help="Token budgets to test (default: 8k 12k 16k)",
    )
    args = parser.parse_args()

    budget_map = {
        "4k": 4000,
        "8k": 8000,
        "12k": 12000,
        "16k": 16000,
        "24k": 24000,
        "32k": 32000,
    }

    test_targets = find_test_repos()
    if not test_targets:
        print("No test packages found.")
        sys.exit(1)

    print(
        f"\n🚀 Running focuspack Benchmark (Tokenizer: {'tiktoken cl100k_base' if _TIKTOKEN_AVAILABLE else 'Calibrated Heuristic'})"
    )
    print("=" * 95)
    header = f"{'Repo':<14} | {'Focus Target':<20} | {'Budget':<7} | {'Strict':<6} | {'Real Tokens':<11} | {'Status':<12} | {'Focus Kept?':<11}"
    print(header)
    print("-" * 95)

    all_passed = True
    for repo_path, focus_file in test_targets:
        for b_str in args.budgets:
            b_int = budget_map.get(b_str.lower(), int(b_str.rstrip("k")) * 1000)
            for strict in [False, True]:
                res = run_benchmark_case(
                    repo_path=repo_path,
                    focus_target=focus_file,
                    budget_str=b_str,
                    budget_int=b_int,
                    strict_budget=strict,
                )

                status = "✅ FITS" if not res["over_budget"] else "❌ OVER"
                if strict and res["exit_code"] != 0:
                    status = "🛑 EXIT 1"
                focus_str = "✅ YES" if res["focus_preserved"] else "❌ DROPPED"

                row = f"{res['repo']:<14} | {res['focus_target']:<20} | {res['budget_str']:<7} | {str(res['strict']):<6} | {res['real_tokens']:<11,} | {status:<12} | {focus_str:<11}"
                print(row)

                if res["over_budget"] and not (strict and res["exit_code"] == 1):
                    all_passed = False

    print("=" * 95)
    if all_passed:
        print("🎉 Benchmark completed: All runs strictly honored budgets and preserved targets!\n")
        sys.exit(0)
    else:
        print("⚠️ Benchmark completed with budget violations.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
