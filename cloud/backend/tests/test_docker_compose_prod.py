"""Guardrails for cloud production Docker build configuration."""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
COMPOSE_FILE = REPO_ROOT / "cloud" / "docker-compose.prod.yml"
BACKEND_DOCKERFILE = REPO_ROOT / "cloud" / "backend" / "Dockerfile.prod"


def test_cloud_backend_prod_build_uses_repo_root_context() -> None:
    compose = yaml.safe_load(COMPOSE_FILE.read_text())
    backend_build = compose["services"]["cloud-backend"]["build"]

    assert backend_build["context"] == ".."
    assert backend_build["dockerfile"] == "cloud/backend/Dockerfile.prod"


def test_cloud_backend_dockerfile_copy_paths_exist_in_repo_root_context() -> None:
    dockerfile = BACKEND_DOCKERFILE.read_text()
    copy_sources = [
        line.split()[1]
        for line in dockerfile.splitlines()
        if line.startswith("COPY ") and not line.startswith("COPY --")
    ]

    for source in copy_sources:
        assert (REPO_ROOT / source).exists(), f"missing COPY source: {source}"
