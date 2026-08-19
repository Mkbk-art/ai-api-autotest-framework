"""Stage 7.1 自由文本脱敏的 TDD 测试。"""
from utils.sanitizer import sanitize_text


def test_sanitize_text_masks_common_secrets_and_personal_data():
    """常见凭据与个人信息不得进入模型文本输入。"""
    raw = (
        "Authorization: Bearer secret-bearer-123\n"
        "token=secret-token-456\n"
        "password=secret-password-789\n"
        "Cookie: session=secret-cookie\n"
        "api_key=secret-key\n"
        "email=user@example.com phone=13812345678"
    )

    safe = sanitize_text(raw)

    for secret in (
        "secret-bearer-123",
        "secret-token-456",
        "secret-password-789",
        "secret-cookie",
        "secret-key",
        "user@example.com",
        "13812345678",
    ):
        assert secret not in safe
    assert "***" in safe


def test_sanitize_text_preserves_non_sensitive_failure_context():
    """脱敏不能把真正用于排障的 AssertionError/JSONPath/业务码一起删掉。"""
    raw = "AssertionError: $.code expected='0' actual='A000001'"

    safe = sanitize_text(raw)

    assert "AssertionError" in safe
    assert "$.code" in safe
    assert "A000001" in safe
