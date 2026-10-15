"""
Configuration constants, default patterns, and models for focuspack.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from re import Pattern


def parse_size_or_tokens(val_str: str | int) -> int:
    """Parse tokens or sizes like '32k', '64k', '100000', or '500kb' into integers."""
    if isinstance(val_str, (int, float)):
        return int(val_str)
    clean = str(val_str).strip().lower()
    if clean.endswith("k") or clean.endswith("kb"):
        num = float(clean.rstrip("kb").rstrip("k"))
        return int(num * 1000)
    elif clean.endswith("m") or clean.endswith("mb"):
        num = float(clean.rstrip("mb").rstrip("m"))
        return int(num * 1_000_000)
    return int(clean)


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
    "/build/",
    "/dist/",
    ".eggs/",
    # Virtual environments
    ".venv/",
    "venv/",
    "/ENV/",
    "/env/",
    # JavaScript / Node
    "node_modules/",
    ".npm/",
    ".yarn/",
    ".pnpm-store/",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    # Rust / Go / Java / Other build artifacts (anchored to root to avoid dropping packages)
    "/target/",
    "/bin/",
    "/obj/",
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
    # focuspack outputs (anchored to root so valid context.py / digest.py packages are kept)
    "*.focuspack.md",
    "*.focuspack.xml",
    "*.focuspack.json",
    "/context.*",
    "/digest.*",
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
        "Anthropic API Key",
        re.compile(r"\b(sk-ant-[A-Za-z0-9_-]{20,})\b"),
    ),
    (
        "OpenAI API Key",
        re.compile(r"\b(sk-(?!ant-)[A-Za-z0-9_-]{20,})\b"),
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
        "Database Credentials",
        re.compile(
            r"(?i)\b(?:postgres|postgresql|mysql|mongodb|mongodb\+srv|redis|rediss|amqp|mssql):\/\/[^\s:@/]+:([^\s@/]+)@[^\s/]+"
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
    include_peripherals: bool = (
        False  # If True, includes peripheral files in file contents even when focus is active
    )
    token_budget: int | None = None  # e.g., 32000, 64000
    strict_budget: bool = False  # If True, fail with error if budget cannot be met
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

    @classmethod
    def from_file(cls, path: Path | str, root_path: str = ".") -> FocusPackConfig:
        """Load configuration from a JSON file, mapping its keys to config fields."""
        cfg_path = Path(path)
        if not cfg_path.is_file():
            raise FileNotFoundError(f"Config file not found: {cfg_path}")

        data = json.loads(cfg_path.read_text(encoding="utf-8"))
        cfg = cls(root_path=root_path)

        if "output_format" in data:
            cfg.output_format = str(data["output_format"]).lower()
        if "mode" in data:
            cfg.mode = str(data["mode"]).lower()
        if "token_budget" in data and data["token_budget"] is not None:
            cfg.token_budget = parse_size_or_tokens(data["token_budget"])
        if "strict_budget" in data:
            cfg.strict_budget = bool(data["strict_budget"])
        if "focus_depth" in data:
            cfg.focus_depth = int(data["focus_depth"])
        if "include_peripherals" in data:
            cfg.include_peripherals = bool(data["include_peripherals"])
        if "focus_targets" in data and isinstance(data["focus_targets"], list):
            cfg.focus_targets = list(data["focus_targets"])
        if "max_size" in data:
            cfg.max_file_size_bytes = parse_size_or_tokens(data["max_size"])
        if "exclude" in data and isinstance(data["exclude"], list):
            cfg.exclude_patterns = list(data["exclude"])
        if "include" in data and isinstance(data["include"], list):
            cfg.include_patterns = list(data["include"])
        if "respect_gitignore" in data:
            cfg.respect_gitignore = bool(data["respect_gitignore"])
        if "redact_secrets" in data:
            cfg.redact_secrets = bool(data["redact_secrets"])
        if "include_tree" in data:
            cfg.include_tree = bool(data["include_tree"])
        if "output_file" in data:
            cfg.output_file = str(data["output_file"])
        if "task" in data or "task_template" in data:
            cfg.task_template = data.get("task") or data.get("task_template")

        return cfg

    @classmethod
    def find_and_load(
        cls, root_path: str = ".", explicit_config: Path | str | None = None
    ) -> FocusPackConfig:
        """
        Locate and load .focuspack.json if present, or return default config.
        """
        if explicit_config:
            return cls.from_file(explicit_config, root_path=root_path)

        candidate = Path(root_path) / ".focuspack.json"
        if candidate.is_file():
            try:
                return cls.from_file(candidate, root_path=root_path)
            except Exception:
                pass
        return cls(root_path=root_path)
