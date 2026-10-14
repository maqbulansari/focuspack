"""
Codebase analysis, token estimation, and metrics module for repodigest.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from focuspack.collector import CollectedFile

# Global tokenizer cache
_TIKTOKEN_ENCODER = None
_TIKTOKEN_CHECKED = False


def _get_tiktoken_encoder():
    global _TIKTOKEN_ENCODER, _TIKTOKEN_CHECKED
    if not _TIKTOKEN_CHECKED:
        _TIKTOKEN_CHECKED = True
        try:
            import tiktoken

            _TIKTOKEN_ENCODER = tiktoken.get_encoding("cl100k_base")
        except Exception:
            _TIKTOKEN_ENCODER = None
    return _TIKTOKEN_ENCODER


@dataclass
class RepoStats:
    """Summary metrics of the collected repository."""

    total_files: int = 0
    total_lines: int = 0
    total_bytes: int = 0
    total_tokens: int = 0
    extension_counts: dict[str, int] = field(default_factory=dict)
    extension_bytes: dict[str, int] = field(default_factory=dict)
    extension_tokens: dict[str, int] = field(default_factory=dict)


class Analyzer:
    """Computes code metrics, token estimations, and language breakdowns."""

    @classmethod
    def estimate_tokens(cls, text: str) -> int:
        """
        Estimate token count using tiktoken if available,
        or a high-accuracy heuristic calibrated for source code.
        """
        if not text:
            return 0

        encoder = _get_tiktoken_encoder()
        if encoder is not None:
            try:
                return len(encoder.encode(text, disallowed_special=()))
            except Exception:
                pass

        # High-accuracy fallback heuristic for source code and markdown
        # Words + punctuation + special code tokens
        # Heuristic: ~3.8 characters per token on average for code/text
        parts = re.findall(r"\w+|[^\w\s]|\s+", text)
        estimated = 0
        for part in parts:
            if part.isspace():
                # Whitespace runs (indents, newlines)
                estimated += max(1, len(part) // 4)
            elif len(part) > 6:
                # Long words / identifiers often split into multiple sub-word tokens
                estimated += max(1, (len(part) + 2) // 4)
            else:
                estimated += 1

        return max(1, estimated)

    @staticmethod
    def format_bytes(size_bytes: int) -> str:
        """Format bytes into human-readable string (KB, MB)."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.2f} MB"

    @classmethod
    def compute_stats(cls, files: list[CollectedFile]) -> RepoStats:
        """Aggregate stats across all collected files."""
        stats = RepoStats()
        for f in files:
            stats.total_files += 1
            stats.total_lines += f.line_count
            stats.total_bytes += f.byte_size
            stats.total_tokens += f.token_count

            ext = f.extension or "(no ext)"
            stats.extension_counts[ext] = stats.extension_counts.get(ext, 0) + 1
            stats.extension_bytes[ext] = stats.extension_bytes.get(ext, 0) + f.byte_size
            stats.extension_tokens[ext] = stats.extension_tokens.get(ext, 0) + f.token_count

        return stats
