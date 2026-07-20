"""Health endpoint reports deployed app version."""


def test_health_includes_version_and_build_time(client, monkeypatch):
    monkeypatch.setenv("APP_VERSION", "1.2.3")
    monkeypatch.setenv("APP_BUILD_TIME", "202607201045")

    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["version"] == "1.2.3"
    assert body["build_time"] == "202607201045"


def test_health_defaults_when_env_unset(client, monkeypatch):
    monkeypatch.delenv("APP_VERSION", raising=False)
    monkeypatch.delenv("APP_BUILD_TIME", raising=False)

    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["version"] == "0.0.0-dev"
    assert body.get("build_time") in (None, "")
