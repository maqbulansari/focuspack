"""
repodigest: Fast, intelligent codebase packaging & AST-aware context generator.
"""

__version__ = "0.1.0"
__author__ = "repodigest contributors"
__license__ = "MIT"

from repodigest.analyzer import Analyzer, RepoStats
from repodigest.ast_parser import ASTParser
from repodigest.collector import CollectedFile, Collector
from repodigest.formatter import Formatter, OutputFormat
from repodigest.security import Finding, SecurityScanner

__all__ = [
    "ASTParser",
    "Analyzer",
    "CollectedFile",
    "Collector",
    "Finding",
    "Formatter",
    "OutputFormat",
    "RepoStats",
    "SecurityScanner",
    "__version__",
]
