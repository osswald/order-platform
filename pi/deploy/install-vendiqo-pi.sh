#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/vendiqo/pi"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

install -d -m 0755 "$APP_DIR"
install -d -m 0755 "$APP_DIR/ota-state"
install -m 0644 "$SCRIPT_DIR/../docker-compose.prod.yml" "$APP_DIR/docker-compose.prod.yml"
install -m 0755 "$SCRIPT_DIR/pi-ota-update.sh" "$APP_DIR/pi-ota-update.sh"
if [ -f "$SCRIPT_DIR/pi.prod.env" ]; then
  install -m 0644 "$SCRIPT_DIR/pi.prod.env" "$APP_DIR/.env"
fi

if [ -f "$SCRIPT_DIR/vendiqo-pi.service" ]; then
  install -m 0644 "$SCRIPT_DIR/vendiqo-pi.service" /etc/systemd/system/vendiqo-pi.service
fi
if [ -f "$SCRIPT_DIR/vendiqo-pi-update.service" ]; then
  install -m 0644 "$SCRIPT_DIR/vendiqo-pi-update.service" /etc/systemd/system/vendiqo-pi-update.service
fi
if [ -f "$SCRIPT_DIR/vendiqo-pi-update.timer" ]; then
  install -m 0644 "$SCRIPT_DIR/vendiqo-pi-update.timer" /etc/systemd/system/vendiqo-pi-update.timer
fi
if [ -f "$SCRIPT_DIR/networkmanager-vendiqo-eth0.nmconnection" ]; then
  install -d -m 0700 /etc/NetworkManager/system-connections
  install -m 0600 "$SCRIPT_DIR/networkmanager-vendiqo-eth0.nmconnection" \
    /etc/NetworkManager/system-connections/vendiqo-eth0.nmconnection
fi

systemctl daemon-reload
systemctl enable vendiqo-pi.service vendiqo-pi-update.timer

echo "Vendiqo Pi files installed. Reboot, then open http://192.168.192.10 to pair."
echo "OTA: pi-ota-update.sh (freeze on prod events, OnBootSec=5min via vendiqo-pi-update.timer)."
