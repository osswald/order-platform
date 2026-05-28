#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Build a generic Vendiqo Raspberry Pi image with sdm.

Usage:
  sudo sd-card-creator/build-sdm-image.sh --base-img /path/raspios.img [--output-dir /path/out]

Environment:
  SDM_BIN       Path to sdm executable. Default: /usr/local/sdm/sdm, then sdm from PATH.
  SDM_CUSTOMIZE_ARGS
                Extra arguments before --customize.
                Default: "--batch --extend --xmb 2048" for unattended builds
                with enough space for Docker and updates.
  IMAGE_NAME    Output image base name. Default: vendiqo-pi-YYYYmmdd-HHMM.img

The resulting image contains no appliance secret. Pair the Pi on first boot at:
  http://192.168.192.10
USAGE
}

BASE_IMG=""
OUTPUT_DIR=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --base-img)
      BASE_IMG="${2:-}"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ -z "$BASE_IMG" ]; then
  echo "--base-img is required" >&2
  usage >&2
  exit 2
fi

if [ "$(id -u)" -ne 0 ]; then
  echo "sdm image customization needs root privileges; rerun with sudo." >&2
  exit 1
fi

if [ ! -f "$BASE_IMG" ]; then
  echo "Base image not found: $BASE_IMG" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PI_DIR="$(cd "$SCRIPT_DIR/../pi" && pwd)"
DEPLOY_DIR="$PI_DIR/deploy"
OUTPUT_DIR="${OUTPUT_DIR:-$SCRIPT_DIR/output}"
IMAGE_NAME="${IMAGE_NAME:-vendiqo-pi-$(date +%Y%m%d-%H%M).img}"
WORK_IMG="$OUTPUT_DIR/$IMAGE_NAME"

if [ -n "${SDM_BIN:-}" ]; then
  SDM="$SDM_BIN"
elif [ -x /usr/local/sdm/sdm ]; then
  SDM="/usr/local/sdm/sdm"
else
  SDM="$(command -v sdm || true)"
fi

if [ -z "$SDM" ]; then
  echo "sdm not found. Install it from https://github.com/gitbls/sdm first." >&2
  exit 1
fi

NMCONN="$DEPLOY_DIR/networkmanager-vendiqo-eth0.nmconnection"
for required in \
  "$PI_DIR/docker-compose.prod.yml" \
  "$DEPLOY_DIR/vendiqo-pi.service" \
  "$DEPLOY_DIR/vendiqo-pi-update.service" \
  "$DEPLOY_DIR/vendiqo-pi-update.timer" \
  "$NMCONN"
do
  if [ ! -f "$required" ]; then
    echo "Missing deploy asset: $required" >&2
    exit 1
  fi
done

mkdir -p "$OUTPUT_DIR"
cp "$BASE_IMG" "$WORK_IMG"

SDM_ARGS=()
SDM_CUSTOMIZE_ARGS="${SDM_CUSTOMIZE_ARGS:---batch --extend --xmb 2048}"
if [ -n "$SDM_CUSTOMIZE_ARGS" ]; then
  # Intentionally split like shell arguments so callers can pass SDM flags.
  # shellcheck disable=SC2206
  SDM_ARGS=(${SDM_CUSTOMIZE_ARGS})
fi

# SDM plugins: packages, Docker, static eth0, Vendiqo unit files, enabled services.
SDM_PLUGIN_ARGS=(
  --plugin "apps:apps=ca-certificates,curl,network-manager,xz-utils"
  --plugin docker-install
  --plugin "network:nmconn=${NMCONN}"
  --plugin "copyfile:from=${PI_DIR}/docker-compose.prod.yml|to=/opt/vendiqo/pi|mkdirif|chmod=644"
  --plugin "copyfile:from=${DEPLOY_DIR}/vendiqo-pi.service|to=/etc/systemd/system|chmod=644"
  --plugin "copyfile:from=${DEPLOY_DIR}/vendiqo-pi-update.service|to=/etc/systemd/system|chmod=644"
  --plugin "copyfile:from=${DEPLOY_DIR}/vendiqo-pi-update.timer|to=/etc/systemd/system|chmod=644"
  --plugin "system:name=vendiqo|service-enable=NetworkManager.service,docker.service,vendiqo-pi.service,vendiqo-pi-update.timer"
)

"$SDM" "${SDM_ARGS[@]}" --customize "$WORK_IMG" \
  "${SDM_PLUGIN_ARGS[@]}"

xz -T0 -f -k "$WORK_IMG"

echo "Built image: $WORK_IMG"
echo "Compressed image: $WORK_IMG.xz"
