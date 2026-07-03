"""Write and remove Caddy route snippets for hosted Pi subdomains."""

from __future__ import annotations

import logging
import subprocess

from .config import CADDY_CONTAINER, CADDY_SNIPPETS_DIR, HOSTED_PI_BASE_DOMAIN
from .slug import safe_path_under, validate_slug

log = logging.getLogger(__name__)


def snippet_path(slug: str):
    validate_slug(slug)
    return safe_path_under(CADDY_SNIPPETS_DIR, f"{slug}.caddy")


def write_snippet(slug: str, frontend_container: str) -> None:
    CADDY_SNIPPETS_DIR.mkdir(parents=True, exist_ok=True)
    host = f"{slug}.{HOSTED_PI_BASE_DOMAIN}"
    body = (
        f"{host} {{\n"
        f"\timport security_headers\n"
        f"\treverse_proxy {frontend_container}:80 {{\n"
        f"\t\theader_down -Server\n"
        f"\t}}\n"
        f"}}\n"
    )
    snippet_path(slug).write_text(body, encoding="utf-8")
    reload_caddy()


def remove_snippet(slug: str) -> None:
    path = snippet_path(slug)
    if path.exists():
        path.unlink()
    reload_caddy()


def reload_caddy() -> None:
    try:
        subprocess.run(
            ["docker", "exec", CADDY_CONTAINER, "caddy", "reload", "--config", "/etc/caddy/Caddyfile"],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        log.warning("Caddy reload failed: %s", exc.stderr or exc.stdout)
