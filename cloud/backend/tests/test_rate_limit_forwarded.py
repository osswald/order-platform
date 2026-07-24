"""Rate-limit client key uses X-Forwarded-For when trusted (security backlog F9)."""

from app.rate_limit import client_ip_key
from starlette.requests import Request


def _request(headers: dict[str, str], client_host: str = "10.0.0.1") -> Request:
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": (client_host, 12345),
        "server": ("test", 80),
    }
    return Request(scope)


def test_client_ip_key_uses_peer_when_proxy_untrusted(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_TRUST_PROXY", "false")
    req = _request({"X-Forwarded-For": "203.0.113.9, 10.0.0.1"})
    assert client_ip_key(req) == "10.0.0.1"


def test_client_ip_key_uses_leftmost_forwarded_when_trusted(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_TRUST_PROXY", "true")
    req = _request({"X-Forwarded-For": "203.0.113.9, 10.0.0.1"})
    assert client_ip_key(req) == "203.0.113.9"


def test_client_ip_key_falls_back_when_forwarded_empty(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_TRUST_PROXY", "true")
    req = _request({})
    assert client_ip_key(req) == "10.0.0.1"
