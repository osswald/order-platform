#!/usr/bin/env bash
# Shared helpers for sd-card-creator native builds.
# shellcheck shell=bash

sdm_creator_dir() {
  local src="${BASH_SOURCE[1]:-${BASH_SOURCE[0]}}"
  while [ -h "$src" ]; do
    local dir
    dir="$(cd -P "$(dirname "$src")" && pwd)"
    src="$(readlink "$src")"
    [[ "$src" != /* ]] && src="$dir/$src"
  done
  cd -P "$(dirname "$src")/.." && pwd
}

load_sdm_creator_env() {
  local root
  root="$(sdm_creator_dir)"

  if [ -f "$root/.env" ]; then
  # shellcheck disable=SC1090
    set -a
    . "$root/.env"
    set +a
  elif [ -f "$root/.env.example" ]; then
  # shellcheck disable=SC1090
    set -a
    . "$root/.env.example"
    set +a
  fi

  if [ -z "${BASE_IMG_URL:-}" ]; then
    echo "error: BASE_IMG_URL is not set. Copy .env.example to .env or edit .env.example." >&2
    return 1
  fi
}

ensure_base_image() {
  local base_img="${1:?base image path required}"

  if [ -s "$base_img" ]; then
    echo "Using existing $base_img (remove it to force a fresh download)."
    return 0
  fi

  if [ -z "${BASE_IMG_URL:-}" ]; then
    echo "error: BASE_IMG_URL is not set." >&2
    return 1
  fi

  echo "Downloading base image from BASE_IMG_URL..."
  local tmp_xz="${base_img}.xz"
  case "${BASE_IMG_URL}" in
    *.img.xz | *.IMG.XZ)
      curl -fSL "${BASE_IMG_URL}" -o "$tmp_xz"
      xz -d -f "$tmp_xz"
      ;;
    *.img | *.IMG)
      curl -fSL "${BASE_IMG_URL}" -o "$base_img"
      ;;
    *)
      echo "error: BASE_IMG_URL must end with .img or .img.xz (got: ${BASE_IMG_URL})" >&2
      return 1
      ;;
  esac

  if [ ! -s "$base_img" ]; then
    echo "error: base image missing or empty after download: $base_img" >&2
    return 1
  fi
}
