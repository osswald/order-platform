#!/usr/bin/env bash
set -euo pipefail

phase="${1:-}"
pfx="$(basename "$0")"

load_sdm_params() {
  if [ -n "${csrc:-}" ]; then
    return
  fi

  if [ -n "${SDMPT:-}" ] && [ -f "$SDMPT/etc/sdm/sdm-readparams" ]; then
    # SDM v15 runs custom scripts as child processes, so --csrc is not exported.
    # Source the generated params file to recover csrc during phase 0.
    # shellcheck disable=SC1090
    . "$SDMPT/etc/sdm/sdm-readparams"
  elif [ -f /etc/sdm/sdm-readparams ]; then
    # shellcheck disable=SC1091
    . /etc/sdm/sdm-readparams
  fi
}

install_docker_compose() {
  if apt-get install -y --no-install-recommends docker-compose-plugin; then
    return
  fi

  if apt-get install -y --no-install-recommends docker-compose-v2; then
    return
  fi

  install -d -m 0755 /usr/local/lib/docker/cli-plugins
  curl -fsSL \
    https://github.com/docker/compose/releases/latest/download/docker-compose-linux-aarch64 \
    -o /usr/local/lib/docker/cli-plugins/docker-compose
  chmod 0755 /usr/local/lib/docker/cli-plugins/docker-compose
}

log() {
  echo "* $pfx $*"
}

load_sdm_params

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
    docker-cli \
    docker.io \
    network-manager \
    xz-utils
  install_docker_compose
  docker compose version

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
