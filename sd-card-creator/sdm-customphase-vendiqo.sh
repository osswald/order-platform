#!/usr/bin/env bash
set -euo pipefail

phase="${1:-}"
pfx="$(basename "$0")"

log() {
  if command -v logtoboth >/dev/null 2>&1; then
    logtoboth "* $pfx $*"
  else
    echo "* $pfx $*"
  fi
}

if [ "$phase" = "0" ]; then
  : "${SDMPT:?SDMPT must be set by sdm in phase 0}"
  : "${csrc:?Pass --csrc /path/to/repo/pi to sdm}"

  log "copy Vendiqo Pi assets into image"
  install -d -m 0755 "$SDMPT/opt/vendiqo/pi"
  install -m 0644 "$csrc/docker-compose.prod.yml" "$SDMPT/opt/vendiqo/pi/docker-compose.prod.yml"

  install -d -m 0755 "$SDMPT/usr/local/share/vendiqo-pi"
  install -m 0755 "$csrc/deploy/install-vendiqo-pi.sh" "$SDMPT/usr/local/share/vendiqo-pi/install-vendiqo-pi.sh"
  install -m 0644 "$csrc/deploy/vendiqo-pi.service" "$SDMPT/etc/systemd/system/vendiqo-pi.service"
  install -m 0644 "$csrc/deploy/vendiqo-pi-update.service" "$SDMPT/etc/systemd/system/vendiqo-pi-update.service"
  install -m 0644 "$csrc/deploy/vendiqo-pi-update.timer" "$SDMPT/etc/systemd/system/vendiqo-pi-update.timer"

  install -d -m 0700 "$SDMPT/etc/NetworkManager/system-connections"
  install -m 0600 "$csrc/deploy/networkmanager-vendiqo-eth0.nmconnection" \
    "$SDMPT/etc/NetworkManager/system-connections/vendiqo-eth0.nmconnection"

elif [ "$phase" = "1" ]; then
  log "install Docker, compose plugin, and NetworkManager"
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    docker.io \
    docker-compose-plugin \
    network-manager \
    xz-utils

  systemctl enable NetworkManager.service
  systemctl enable docker.service
  systemctl enable vendiqo-pi.service
  systemctl enable vendiqo-pi-update.timer

elif [ "$phase" = "post-install" ]; then
  log "post-install complete"
else
  echo "Unknown sdm phase: $phase" >&2
  exit 1
fi
