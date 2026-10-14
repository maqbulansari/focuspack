"""Tests for Adaptive Token Budgeting."""

from pathlib import Path

from focuspack.analyzer import Analyzer
from focuspack.budget import BudgetOptimizer
from focuspack.collector import CollectedFile
from focuspack.graph import FileRole


def make_file(name: str, code: str, role: FileRole) -> CollectedFile:
    tokens = Analyzer.estimate_tokens(code)
    lines = len(code.splitlines())
    return CollectedFile(
        relative_path=name,
        absolute_path=Path(name),
        extension=".py",
        content=code,
        line_count=lines,
        byte_size=len(code.encode("utf-8")),
        token_count=tokens,
        mode="full",
        role=role,
    )


def test_budget_optimizer_under_budget():
    files = [make_file("main.py", "x = 1", FileRole.FOCUS_TARGET)]
    optimized, report = BudgetOptimizer.optimize(files, budget_tokens=1000)
    assert report.is_within_budget
    assert len(optimized) == 1
    assert optimized[0].mode == "full"


def test_budget_optimizer_downgrades_peripheral():
    large_function = "def long_func():\n" + ("    a = 1\n" * 100)
    focus = make_file("focus.py", "def my_func(): pass", FileRole.FOCUS_TARGET)
    peripheral = make_file("helper.py", large_function, FileRole.PERIPHERAL)

    files = [focus, peripheral]
    initial_tokens = focus.token_count + peripheral.token_count

    # Set budget lower than initial total
    budget = initial_tokens // 2
    optimized, report = BudgetOptimizer.optimize(files, budget_tokens=budget)

    # Should downgrade or prune peripheral while keeping focus full
    focus_res = next(f for f in optimized if f.relative_path == "focus.py")
    assert focus_res.mode == "full"
    assert report.final_tokens <= initial_tokens
