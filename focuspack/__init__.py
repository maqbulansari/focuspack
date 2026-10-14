"""
focuspack: Focus-driven, budget-aware codebase context packager for LLMs.
"""

__version__ = "0.2.0"
__author__ = "focuspack contributors"
__license__ = "MIT"

from focuspack.analyzer import Analyzer, RepoStats
from focuspack.ast_parser import ASTParser
from focuspack.budget import BudgetOptimizer, BudgetReport
from focuspack.collector import CollectedFile, Collector
from focuspack.formatter import Formatter, OutputFormat
from focuspack.graph import DependencyGraph, FileRole
from focuspack.security import Finding, SecurityScanner
from focuspack.templates import get_task_instruction

__all__ = [
    "__version__",
    "Collector",
    "CollectedFile",
    "DependencyGraph",
    "FileRole",
    "BudgetOptimizer",
    "BudgetReport",
    "Analyzer",
    "RepoStats",
    "ASTParser",
    "Formatter",
    "OutputFormat",
    "SecurityScanner",
    "Finding",
    "get_task_instruction",
]
