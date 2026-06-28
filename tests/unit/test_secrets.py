from cascade.diff_parser import FileDiff
from cascade.analyzers.static.secrets import scan


def _file(added_lines):
    return [FileDiff(path="test.py", language="python", added_lines=added_lines)]


def test_detects_api_key():
    findings = scan(_file(['API_KEY = "sk-proj-abc123def456ghi789jkl012mno345pqr678stu901vwx234"']))
    assert len(findings) >= 1
    assert findings[0].secret_type == "API Key"
    assert findings[0].severity == "CRITICAL"


def test_detects_aws_key():
    findings = scan(_file(['AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"']))
    assert len(findings) >= 1
    assert "AWS" in findings[0].secret_type


def test_detects_private_key():
    findings = scan(_file(['-----BEGIN RSA PRIVATE KEY-----']))
    assert len(findings) >= 1
    assert "Private Key" in findings[0].secret_type


def test_detects_stripe_key():
    fake_stripe = "sk_live_" + "X" * 24
    findings = scan(_file([f'STRIPE = "{fake_stripe}"']))
    assert len(findings) >= 1


def test_detects_jwt():
    fake_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmYWtlIjoiZGF0YSJ9.FAKESIGNATUREDATA12345"
    findings = scan(_file([f'token = "{fake_jwt}"']))
    assert len(findings) >= 1
    assert findings[0].secret_type == "JWT Token"


def test_detects_slack_token():
    findings = scan(_file(['token = "' + "xox" + "b-" + "0" * 10 + "-" + "A" * 16 + '"']))
    assert len(findings) >= 1


def test_no_false_positive_on_clean_code():
    findings = scan(_file([
        'name = "hello"',
        'count = 42',
        'import os',
    ]))
    assert len(findings) == 0


def test_truncates_long_lines():
    long_secret = "-----BEGIN RSA PRIVATE KEY-----" + "A" * 200
    findings = scan(_file([long_secret]))
    assert len(findings) >= 1
    assert len(findings[0].line_content) <= 80
