"""Tests for SecurityScanner."""

from focuspack.security import SecurityScanner


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


def test_database_credentials_redaction():
    scanner = SecurityScanner()
    code = 'DATABASE_URL = "postgres://admin:hunter2pass@host.internal:5432/production_db"'
    findings = scanner.scan_text(code, "settings.py")
    assert len(findings) == 1
    assert findings[0].pattern_name == "Database Credentials"
    assert "hunter2pass" not in findings[0].matched_preview

    redacted, count = scanner.redact_text(code)
    assert count == 1
    assert "hunter2pass" not in redacted
    assert (
        "postgres://admin:[REDACTED_SECRET: Database Credentials]@host.internal:5432/production_db"
        in redacted
    )


def test_anthropic_key_not_mislabeled_as_openai():
    scanner = SecurityScanner()
    code = (
        'anthropic_client = Anthropic(api_key="sk-ant-api03-abcdefghijklmnopqrstuvwxyz1234567890")'
    )
    findings = scanner.scan_text(code, "ai.py")
    assert len(findings) == 1
    # Must be recognized as Anthropic API Key, NOT OpenAI API Key
    assert findings[0].pattern_name == "Anthropic API Key"
    redacted, count = scanner.redact_text(code)
    assert count == 1
    assert "[REDACTED_SECRET: Anthropic API Key]" in redacted
