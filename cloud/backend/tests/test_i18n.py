"""i18n helpers and locale resolution."""

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.i18n import DEFAULT_LOCALE, normalize_locale, resolve_locale_from_accept_language, t
from app.i18n.deps import get_locale


def test_t_nested_key():
    assert t("errors.incorrect_email_or_password", "de") == "E-Mail oder Passwort ist falsch."


def test_t_interpolation():
    msg = t("errors.stock_insufficient", "de", available=3, name="Bier")
    assert "3" in msg
    assert "Bier" in msg


def test_t_missing_key_returns_key():
    assert t("errors.nonexistent_key", "de") == "errors.nonexistent_key"


def test_resolve_locale_from_accept_language():
    assert resolve_locale_from_accept_language("de-CH,de;q=0.9") == "de"
    assert resolve_locale_from_accept_language("en-US,en;q=0.8") == "en"
    assert resolve_locale_from_accept_language(None) == DEFAULT_LOCALE


def test_normalize_locale():
    assert normalize_locale("de-CH") == "de"
    assert normalize_locale("en-GB") == "en"
    assert normalize_locale("") == DEFAULT_LOCALE


def test_get_locale_dependency():
    app = FastAPI()

    @app.get("/locale")
    def read_locale(locale: str = Depends(get_locale)):
        return {"locale": locale}

    client = TestClient(app)
    assert client.get("/locale", headers={"Accept-Language": "de-CH"}).json() == {"locale": "de"}
    assert client.get("/locale", headers={"Accept-Language": "en-US"}).json() == {"locale": "en"}
    assert client.get("/locale").json() == {"locale": DEFAULT_LOCALE}
