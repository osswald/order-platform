"""SECRET_KEY validation (security #4)."""

import pytest

from app.security import DEV_DEFAULT_SECRET_KEY, load_secret_key


def test_development_allows_default_secret(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setenv("APP_ENV", "development")
    assert load_secret_key() == DEV_DEFAULT_SECRET_KEY


def test_development_allows_explicit_secret(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("SECRET_KEY", "short-dev-key")
    assert load_secret_key() == "short-dev-key"


def test_production_requires_secret(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="SECRET_KEY must be set"):
        load_secret_key()


def test_production_rejects_placeholder(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", DEV_DEFAULT_SECRET_KEY)
    with pytest.raises(RuntimeError, match="placeholder"):
        load_secret_key()


def test_production_requires_minimum_length(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "a" * 16)
    with pytest.raises(RuntimeError, match="at least"):
        load_secret_key()


def test_production_accepts_strong_secret(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    strong = "x" * 32
    monkeypatch.setenv("SECRET_KEY", strong)
    assert load_secret_key() == strong
