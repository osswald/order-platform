"""Hosted-Pi manager secret verification (security backlog F19)."""

from app.main import _secrets_match


def test_secrets_match_equal():
    assert _secrets_match("expected-secret-value", "expected-secret-value") is True


def test_secrets_match_rejects_wrong_value():
    assert _secrets_match("wrong-secret-value!!", "expected-secret-value") is False


def test_secrets_match_rejects_different_length():
    assert _secrets_match("short", "expected-secret-value") is False


def test_secrets_match_rejects_missing():
    assert _secrets_match(None, "expected-secret-value") is False
    assert _secrets_match("", "expected-secret-value") is False
