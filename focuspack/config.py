"""
Configuration constants, default patterns, and models for focuspack.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from re import Pattern

# Default directory and file ignore patterns (similar to .gitignore syntax)
DEFAULT_IGNORE_PATTERNS: list[str] = [
    # Version control
    ".git/",
    ".svn/",
    ".hg/",
    # Python
    "__pycache__/",
    "*.py[cod]",
    "*$py.class",
    ".pytest_cache/",
    ".mypy_cache/",
    ".ruff_cache/",
    ".tox/",
    ".nox/",
    ".coverage",
    ".coverage.*",
    "htmlcov/",
    "*.egg-info/",
    "build/",
    "dist/",
    ".eggs/",
    # Virtual environments
    ".venv/",
    "venv/",
    "ENV/",
    "env/",
    # JavaScript / Node
    "node_modules/",
    ".npm/",
    ".yarn/",
    ".pnpm-store/",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    # Rust / Go / Java / Other build artifacts
    "target/",
    "bin/",
    "obj/",
    "*.class",
    "*.jar",
    "Cargo.lock",
    "poetry.lock",
    "Gemfile.lock",
    # IDEs and Editors
    ".idea/",
    ".vscode/",
    "*.swp",
    "*.swo",
    "*~",
    ".DS_Store",
    "Thumbs.db",
    # Environment & Secrets (should never be packaged by default!)
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "*.crt",
    "*.cer",
    "*.pfx",
    "*.p12",
    # focuspack outputs
    "*.focuspack.md",
    "*.focuspack.xml",
    "*.focuspack.json",
    "context.xml",
    "context.md",
    "digest.md",
    "digest.xml",
]

# Known binary extensions
BINARY_EXTENSIONS = {
    # Images
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".webp",
    ".bmp",
    ".tiff",
    ".psd",
    # Audio/Video
    ".mp3",
    ".wav",
    ".ogg",
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".flv",
    ".webm",
    # Documents / Executables / Archives
    ".pdf",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".bin",
    ".iso",
    ".dmg",
    ".zip",
    ".tar",
    ".gz",
    ".bz2",
    ".xz",
    ".7z",
    ".rar",
    ".whl",
    # Fonts
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".otf",
    # Database files
    ".sqlite",
    ".sqlite3",
    ".db",
}

# Known sensitive patterns for detection & redaction
SECRET_PATTERNS: list[tuple[str, Pattern[str]]] = [
    (
        "OpenAI API Key",
        re.compile(r"\b(sk-[A-Za-z0-9_-]{20,})\b"),
    ),
    (
        "Anthropic API Key",
        re.compile(r"\b(sk-ant-[A-Za-z0-9_-]{20,})\b"),
    ),
    (
        "GitHub Token",
        re.compile(r"\b(gh[pousr]_[A-Za-z0-9_]{36,}|github_pat_[A-Za-z0-9_]{82})\b"),
    ),
    (
        "AWS Access Key ID",
        re.compile(r"\b((?:AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16})\b"),
    ),
    (
        "AWS Secret Access Key",
        re.compile(
            r"(?i)\baws[_\-]?secret[_\-]?(?:access[_\-])?key\s*[:=]\s*['\"]([0-9a-zA-Z\/+]{40})['\"]"
        ),
    ),
    (
        "Slack Token",
        re.compile(r"\b(xox[baprs]-[0-9a-zA-Z]{10,48})\b"),
    ),
    (
        "Private Key",
        re.compile(
            r"-----BEGIN (?:[A-Z0-9\s]+ )?PRIVATE KEY-----[^-]+-----END (?:[A-Z0-9\s]+ )?PRIVATE KEY-----",
            re.DOTALL,
        ),
    ),
    (
        "Generic Secret/Password Assignment",
        re.compile(
            r"(?i)\b(api_key|apikey|secret|secret_key|auth_token|access_token|password|passwd)\s*[:=]\s*['\"]([^'\"\s]{8,})['\"]"
        ),
    ),
]


@dataclass
class FocusPackConfig:
    """Configuration settings for focuspack execution."""

    root_path: str = "."
    output_format: str = "xml"  # xml (recommended for LLMs), markdown, json, plain
    mode: str = "auto"  # auto (tiered), full, skeleton
    focus_targets: list[str] = field(default_factory=list)  # Files/directories of interest
    focus_depth: int = 1  # How many dependency hops to include
    token_budget: int | None = None  # e.g., 32000, 64000
    task_template: str | None = None  # e.g., "bugfix", "review", "refactor", "explain"
    custom_task_prompt: str | None = None
    max_file_size_bytes: int = 500 * 1024  # 500 KB limit
    include_patterns: list[str] = field(default_factory=list)
    exclude_patterns: list[str] = field(default_factory=list)
    respect_gitignore: bool = True
    redact_secrets: bool = True
    include_tree: bool = True
    output_file: str | None = None
    copy_to_clipboard: bool = False
