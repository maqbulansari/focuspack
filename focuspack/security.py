"""
Security and secret scanning module for repodigest.
Prevents accidental leakage of API keys, tokens, and credentials into AI prompts.
"""

from __future__ import annotations

from dataclasses import dataclass

from focuspack.config import SECRET_PATTERNS


@dataclass
class Finding:
    """Represents a discovered potential secret."""

    pattern_name: str
    file_path: str
    line_number: int
    matched_preview: str

    def __str__(self) -> str:
        return (
            f"[{self.pattern_name}] {self.file_path}:{self.line_number} -> {self.matched_preview}"
        )


class SecurityScanner:
    """Scans and optionally redacts secrets from source code."""

    def __init__(self, patterns=None):
        self.patterns = patterns or SECRET_PATTERNS

    @staticmethod
    def _mask(value: str) -> str:
        """Mask a sensitive string leaving only the prefix and suffix."""
        if len(value) <= 8:
            return "*" * len(value)
        return f"{value[:4]}...{value[-4:]}"

    def _locate_matches(self, content: str) -> list[tuple[int, int, str, str]]:
        """
        Locate non-overlapping secret spans in content.
        Returns list of (start_idx, end_idx, pattern_name, secret_value).
        """
        all_matches: list[tuple[int, int, str, str]] = []
        covered_ranges: list[tuple[int, int]] = []

        for pattern_name, regex in self.patterns:
            for match in regex.finditer(content):
                group_idx = match.lastindex or 0
                start, end = match.span(group_idx)
                secret_val = match.group(group_idx)

                # Skip if already overlapped by an earlier (higher priority) match
                overlaps = any(
                    not (end <= c_start or start >= c_end) for c_start, c_end in covered_ranges
                )
                if not overlaps:
                    covered_ranges.append((start, end))
                    all_matches.append((start, end, pattern_name, secret_val))

        # Sort matches by start position
        all_matches.sort(key=lambda m: m[0])
        return all_matches

    def scan_text(self, content: str, file_path: str = "") -> list[Finding]:
        """Scan string content for sensitive credentials."""
        findings: list[Finding] = []
        matches = self._locate_matches(content)

        for start, _end, pattern_name, secret_val in matches:
            line_no = content[:start].count("\n") + 1
            findings.append(
                Finding(
                    pattern_name=pattern_name,
                    file_path=file_path,
                    line_number=line_no,
                    matched_preview=self._mask(secret_val),
                )
            )

        return findings

    def redact_text(self, content: str) -> tuple[str, int]:
        """
        Redact sensitive credentials from the text.
        Returns (redacted_content, total_redactions_count).
        """
        matches = self._locate_matches(content)
        if not matches:
            return content, 0

        # Replace backwards from end to start to preserve offsets
        cleaned = content
        for start, end, pattern_name, _ in reversed(matches):
            redacted_tag = f"[REDACTED_SECRET: {pattern_name}]"
            cleaned = cleaned[:start] + redacted_tag + cleaned[end:]

        return cleaned, len(matches)
