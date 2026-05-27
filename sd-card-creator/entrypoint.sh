#!/usr/bin/env bash
set -euo pipefail

BASE="/input/base.img"

if [[ -z "${BASE_IMG_URL:-}" ]]; then
  echo "error: BASE_IMG_URL is not set. Copy .env.example to .env and set BASE_IMG_URL." >&2
  exit 1
fi

if [[ -s "$BASE" ]]; then
  echo "Using existing $BASE (remove it to force a fresh download)."
else
  echo "Downloading base image from BASE_IMG_URL..."
  case "${BASE_IMG_URL}" in
    *.img.xz | *.IMG.XZ)
      curl -fSL "${BASE_IMG_URL}" -o /input/base.img.xz
      xz -d /input/base.img.xz
      ;;
    *.img | *.IMG)
      curl -fSL "${BASE_IMG_URL}" -o "$BASE"
      ;;
    *)
      echo "error: BASE_IMG_URL must end with .img or .img.xz (got: ${BASE_IMG_URL})" >&2
      exit 1
      ;;
  esac
fi

if [[ ! -s "$BASE" ]]; then
  echo "error: base image missing or empty after download: $BASE" >&2
  exit 1
fi

if [[ "$(id -u)" -ne 0 ]]; then
  echo "error: this image must run as root (use default Docker user)." >&2
  exit 1
fi

export SDM_BIN="${SDM_BIN:-/usr/local/sdm/sdm}"
exec /workspace/sd-card-creator/build-sdm-image.sh --base-img "$BASE" --output-dir /out
