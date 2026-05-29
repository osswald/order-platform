#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/vendiqo/pi"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

install -d -m 0755 "$APP_DIR"
install -m 0644 "$SCRIPT_DIR/../docker-compose.prod.yml" "$APP_DIR/docker-compose.prod.yml"
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

if [ -f "$SCRIPT_DIR/install-tailscale.sh" ]; then
  bash "$SCRIPT_DIR/install-tailscale.sh"
fi

systemctl daemon-reload
systemctl enable vendiqo-pi.service vendiqo-pi-update.timer

echo "Vendiqo Pi files installed. Reboot, then open http://192.168.192.10 to pair."
