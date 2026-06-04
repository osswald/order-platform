"""Hosted Pi orchestrator configuration."""

import os
from pathlib import Path

MANAGER_SECRET = os.getenv("HOSTED_PI_MANAGER_SECRET", "")
HOSTED_PI_BASE_DOMAIN = os.getenv("HOSTED_PI_BASE_DOMAIN", "demo.vendiqo.ch")
PI_BACKEND_IMAGE = os.getenv(
    "PI_BACKEND_IMAGE",
    "ghcr.io/osswald/order-platform:pi-backend-amd64-latest",
)
PI_FRONTEND_IMAGE = os.getenv(
    "PI_FRONTEND_IMAGE",
    "ghcr.io/osswald/order-platform:pi-frontend-amd64-latest",
)
CADDY_NETWORK = os.getenv("CADDY_NETWORK", "cloud_app-net")
CADDY_CONTAINER = os.getenv("CADDY_CONTAINER", "cloud-caddy-1")
CADDY_SNIPPETS_DIR = Path(os.getenv("CADDY_SNIPPETS_DIR", "/caddy-snippets"))
INSTANCES_DIR = Path(os.getenv("HOSTED_PI_INSTANCES_DIR", "/instances"))
