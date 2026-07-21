#!/usr/bin/env bash
# Run on a running Pi (as root or with sudo) to fix GHCR image paths and restart the stack.
set -euo pipefail

APP_DIR="/opt/vendiqo/pi"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

install -d -m 0755 "$APP_DIR"
install -d -m 0755 "$APP_DIR/ota-state"
install -m 0644 "$SCRIPT_DIR/pi.prod.env" "$APP_DIR/.env"
install -m 0644 "$SCRIPT_DIR/../docker-compose.prod.yml" "$APP_DIR/docker-compose.prod.yml"
install -m 0755 "$SCRIPT_DIR/pi-ota-update.sh" "$APP_DIR/pi-ota-update.sh"
if [ -f "$SCRIPT_DIR/vendiqo-pi.service" ]; then
  install -m 0644 "$SCRIPT_DIR/vendiqo-pi.service" /etc/systemd/system/vendiqo-pi.service
fi
if [ -f "$SCRIPT_DIR/vendiqo-pi-update.service" ]; then
  install -m 0644 "$SCRIPT_DIR/vendiqo-pi-update.service" /etc/systemd/system/vendiqo-pi-update.service
fi
if [ -f "$SCRIPT_DIR/vendiqo-pi-update.timer" ]; then
  install -m 0644 "$SCRIPT_DIR/vendiqo-pi-update.timer" /etc/systemd/system/vendiqo-pi-update.timer
fi
systemctl daemon-reload 2>/dev/null || true

cd "$APP_DIR"
docker compose -f docker-compose.prod.yml pull
systemctl restart vendiqo-pi.service

echo "Updated $APP_DIR/.env and restarted vendiqo-pi.service"
docker compose -f docker-compose.prod.yml ps
