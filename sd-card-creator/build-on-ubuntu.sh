#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
. "$SCRIPT_DIR/lib/common.sh"

usage() {
  cat <<'USAGE'
Build a Vendiqo Pi SD image on Ubuntu (or any Linux host with SDM).

Usage:
  ./build-on-ubuntu.sh

Requires: Linux, curl, sudo, network. Run inside UTM Ubuntu (or native Linux).
Output: sd-card-creator/output/vendiqo-pi-*.img and .xz
USAGE
}

preflight() {
  if [ "$(uname -s)" != "Linux" ]; then
    echo "error: this script must run on Linux (use UTM Ubuntu on macOS)." >&2
    exit 1
  fi

  if ! command -v sudo >/dev/null 2>&1; then
    echo "error: sudo is required." >&2
    exit 1
  fi

  if ! command -v curl >/dev/null 2>&1; then
    echo "error: curl is required. Install with: sudo apt-get install -y curl" >&2
    exit 1
  fi

  local arch
  arch="$(uname -m)"
  if [ "$arch" != "aarch64" ] && [ "$arch" != "arm64" ]; then
    echo "note: host architecture is $arch; SDM will use qemu-user-static for arm64 images."
  fi
}

install_host_deps() {
  if ! command -v apt-get >/dev/null 2>&1; then
    echo "error: apt-get not found; this script targets Debian/Ubuntu." >&2
    exit 1
  fi

  echo "Installing host packages (sudo)..."
  sudo DEBIAN_FRONTEND=noninteractive apt-get update -qq
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    kmod \
    parted \
    udev \
    util-linux \
    xz-utils
}

ensure_sdm() {
  if [ -x /usr/local/sdm/sdm ]; then
    return 0
  fi
  if command -v sdm >/dev/null 2>&1; then
    return 0
  fi

  echo "Installing SDM..."
  curl -fsSL https://raw.githubusercontent.com/gitbls/sdm/master/install-sdm | sudo bash
}

main() {
  if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
    usage
    exit 0
  fi

  preflight
  install_host_deps
  ensure_sdm
  load_sdm_creator_env

  mkdir -p "$SCRIPT_DIR/input" "$SCRIPT_DIR/output"
  ensure_base_image "$SCRIPT_DIR/input/base.img"

  echo "Running SDM image build (sudo)..."
  sudo env SDM_BIN="${SDM_BIN:-/usr/local/sdm/sdm}" \
    "$SCRIPT_DIR/build-sdm-image.sh" \
    --base-img "$SCRIPT_DIR/input/base.img" \
    --output-dir "$SCRIPT_DIR/output"
}

main "$@"
