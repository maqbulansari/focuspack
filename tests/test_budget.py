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


def test_budget_optimizer_stage3_docstring_stripping():
    # Contract with docstring
    contract_code = 'def utility():\n    """This is a very long documentation docstring describing how this works."""\n    return 1\n'
    focus = make_file("focus.py", "x = 1\n", FileRole.FOCUS_TARGET)
    contract = make_file("contract.py", contract_code, FileRole.DEPENDENCY_CONTRACT)

    # Force budget smaller than contract with docstring
    budget = focus.token_count + 5
    optimized, report = BudgetOptimizer.optimize([focus, contract], budget_tokens=budget)
    contract_res = next(f for f in optimized if f.relative_path == "contract.py")
    assert "docstrings describing how" not in contract_res.content


def test_budget_optimizer_compresses_large_focus_target():
    large_body = "\n".join([f"    x_{i} = {i}" for i in range(40)])
    target_code = (
        f"def massive_handler():\n    '''Keep docstring.'''\n{large_body}\n    return True\n"
    )
    target = make_file("target.py", target_code, FileRole.FOCUS_TARGET)

    # Budget is smaller than target token count
    tight_budget = target.token_count // 2
    optimized, report = BudgetOptimizer.optimize([target], budget_tokens=tight_budget)

    target_res = optimized[0]
    assert target_res.mode == "compressed_target"
    assert "target.py" in report.methods_compressed
    assert "..." in target_res.content
    assert "Keep docstring." in target_res.content
    assert target_res.token_count < report.initial_tokens


def test_budget_optimizer_stage5_drops_lowest_ranked_contracts():
    focus = make_file("focus.py", "import c1\ndef main(): pass", FileRole.FOCUS_TARGET)
    c1 = make_file("c1.py", "def f1(): pass", FileRole.DEPENDENCY_CONTRACT)
    c1.depth = 1
    c2 = make_file("c2.py", "def f2(): pass\n" + ("x = 1\n" * 50), FileRole.DEPENDENCY_CONTRACT)
    c2.depth = 2

    files = [focus, c1, c2]

    # Target budget fits focus + c1, but cannot fit c2
    target_budget = focus.token_count + c1.token_count + 10
    optimized, report = BudgetOptimizer.optimize(files, budget_tokens=target_budget)

    kept_paths = [f.relative_path for f in optimized]
    assert "focus.py" in kept_paths
    assert "c1.py" in kept_paths
    assert "c2.py" not in kept_paths
    assert "c2.py" in report.dropped_contracts
    assert report.is_within_budget
