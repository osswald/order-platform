"""Docker Compose lifecycle for hosted Pi instances."""

from __future__ import annotations

import logging
import subprocess
import time
from pathlib import Path

from .caddy import remove_snippet, write_snippet
from .config import (
    CADDY_NETWORK,
    INSTANCES_DIR,
    PI_BACKEND_IMAGE,
    PI_FRONTEND_IMAGE,
)

log = logging.getLogger(__name__)


def _project_name(slug: str) -> str:
    return f"hosted-pi-{slug}"


def _instance_dir(slug: str) -> Path:
    return INSTANCES_DIR / slug


def _frontend_container(slug: str) -> str:
    return f"{_project_name(slug)}-pi-frontend-1"


def _compose_yaml(slug: str, *, cloud_base_url: str, edge_client_id: str, edge_secret: str) -> str:
    return f"""services:
  pi-backend:
    image: {PI_BACKEND_IMAGE}
    pull_policy: always
    restart: unless-stopped
    environment:
      DATABASE_URL: sqlite:////data/pi.db
      EDGE_CONFIG_FILE: /data/edge.env
      CLOUD_BASE_URL: {cloud_base_url}
      EDGE_CLIENT_ID: {edge_client_id}
      EDGE_SECRET: {edge_secret}
      HOSTED_PI: "1"
      PRINTER_MODE: emulated
      SYNC_ENABLED: "1"
      SYNC_PUSH_ENABLED: "0"
      SYNC_INTERVAL_SECONDS: "60"
      APP_NAME: pi-backend
    volumes:
      - pi-data:/data
    networks:
      - pi-net

  pi-frontend:
    image: {PI_FRONTEND_IMAGE}
    pull_policy: always
    restart: unless-stopped
    depends_on:
      - pi-backend
    healthcheck:
      test: ["CMD-SHELL", "wget -q -O /dev/null http://127.0.0.1/ || exit 1"]
      interval: 2s
      timeout: 3s
      retries: 15
      start_period: 5s
    networks:
      - pi-net
      - caddy-net

volumes:
  pi-data: {{}}

networks:
  pi-net:
    driver: bridge
  caddy-net:
    external: true
    name: {CADDY_NETWORK}
"""


def _poll_container_http(container: str, *, timeout_seconds: int = 90, interval_seconds: float = 2) -> None:
    """Wait until nginx inside the frontend container serves the SPA."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        result = subprocess.run(
            ["docker", "exec", container, "wget", "-q", "-O", "/dev/null", "http://127.0.0.1/"],
            capture_output=True,
        )
        if result.returncode == 0:
            return
        time.sleep(interval_seconds)
    raise TimeoutError(f"Container {container} did not respond on port 80 within {timeout_seconds}s")


def provision(slug: str, *, cloud_base_url: str, edge_client_id: str, edge_secret: str) -> None:
    directory = _instance_dir(slug)
    directory.mkdir(parents=True, exist_ok=True)
    compose_file = directory / "docker-compose.yml"
    compose_file.write_text(
        _compose_yaml(slug, cloud_base_url=cloud_base_url, edge_client_id=edge_client_id, edge_secret=edge_secret),
        encoding="utf-8",
    )
    project = _project_name(slug)
    frontend_container = _frontend_container(slug)
    subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            str(compose_file),
            "-p",
            project,
            "up",
            "-d",
            "--pull",
            "always",
            "--wait",
            "--remove-orphans",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    _poll_container_http(frontend_container)
    write_snippet(slug, frontend_container)
    # Caddy reload is async; give routing a moment to settle before exposing the URL.
    _poll_container_http(frontend_container, timeout_seconds=30)
    log.info("Provisioned hosted Pi %s", slug)


def destroy(slug: str) -> None:
    directory = _instance_dir(slug)
    compose_file = directory / "docker-compose.yml"
    project = _project_name(slug)
    if compose_file.exists():
        subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "-p", project, "down", "-v", "--remove-orphans"],
            check=False,
            capture_output=True,
            text=True,
        )
    remove_snippet(slug)
    if directory.exists():
        for child in directory.iterdir():
            child.unlink(missing_ok=True)
        directory.rmdir()
    log.info("Destroyed hosted Pi %s", slug)
