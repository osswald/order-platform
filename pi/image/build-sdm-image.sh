#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Build a generic Vendiqo Raspberry Pi image with sdm.

Usage:
  sudo pi/image/build-sdm-image.sh --base-img /path/raspios.img [--output-dir /path/out]

Environment:
  SDM_BIN       Path to sdm executable. Default: /usr/local/sdm/sdm, then sdm from PATH.
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
PI_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="${OUTPUT_DIR:-$SCRIPT_DIR/out}"
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

mkdir -p "$OUTPUT_DIR"
cp "$BASE_IMG" "$WORK_IMG"

"$SDM" --customize "$WORK_IMG" \
  --cscript "$SCRIPT_DIR/sdm-customphase-vendiqo.sh" \
  --csrc "$PI_DIR"

xz -T0 -f -k "$WORK_IMG"

echo "Built image: $WORK_IMG"
echo "Compressed image: $WORK_IMG.xz"
