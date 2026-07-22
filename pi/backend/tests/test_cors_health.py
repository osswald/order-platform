"""CORS headers on /health for Android WebView origin."""


def test_health_allows_android_webview_origin_without_credentials(client):
    res = client.get(
        "/health",
        headers={"Origin": "https://appassets.androidplatform.net"},
    )
    assert res.status_code == 200
    assert res.json().get("status") == "ok"
    assert res.headers.get("access-control-allow-origin") == "*"
    # Credentialed CORS is intentionally off so '*' is valid.
    assert "access-control-allow-credentials" not in {
        k.lower() for k in res.headers.keys()
    } or res.headers.get("access-control-allow-credentials") in (None, "false")


def test_health_preflight_allows_get(client):
    res = client.options(
        "/health",
        headers={
            "Origin": "https://appassets.androidplatform.net",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert res.status_code in (200, 204)
    assert res.headers.get("access-control-allow-origin") == "*"
