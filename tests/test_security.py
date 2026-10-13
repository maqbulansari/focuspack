"""Tests for SecurityScanner."""

from repodigest.security import SecurityScanner


def test_openai_key_detection_and_redaction():
    scanner = SecurityScanner()
    code = 'client = OpenAI(api_key="sk-abcdefghijklmnopqrstuvwxyz1234567890")'

    findings = scanner.scan_text(code, "config.py")
    assert len(findings) == 1
    assert findings[0].pattern_name == "OpenAI API Key"
    assert findings[0].file_path == "config.py"
    assert "sk-a...7890" in findings[0].matched_preview

    redacted, count = scanner.redact_text(code)
    assert count == 1
    assert "sk-abcdefghijklmnopqrstuvwxyz1234567890" not in redacted
    assert "[REDACTED_SECRET: OpenAI API Key]" in redacted


def test_aws_key_detection():
    scanner = SecurityScanner()
    code = 'AWS_KEY = "AKIAIOSFODNN7EXAMPLE"'

    findings = scanner.scan_text(code, "aws.py")
    assert len(findings) >= 1
    assert any(f.pattern_name == "AWS Access Key ID" for f in findings)


def test_clean_code_no_findings():
    scanner = SecurityScanner()
    code = """
def add(a: int, b: int) -> int:
    return a + b
"""
    findings = scanner.scan_text(code, "math.py")
    assert len(findings) == 0
    redacted, count = scanner.redact_text(code)
    assert count == 0
    assert redacted == code
