#!/usr/bin/env bash
# Run on a running Pi (as root or with sudo) to fix GHCR image paths and restart the stack.
set -euo pipefail

APP_DIR="/opt/vendiqo/pi"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

install -d -m 0755 "$APP_DIR"
install -m 0644 "$SCRIPT_DIR/pi.prod.env" "$APP_DIR/.env"

cd "$APP_DIR"
docker compose -f docker-compose.prod.yml pull
systemctl restart vendiqo-pi.service

echo "Updated $APP_DIR/.env and restarted vendiqo-pi.service"
docker compose -f docker-compose.prod.yml ps
