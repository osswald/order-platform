#!/usr/bin/env bash
# Nightly Play review cleanup: test→prod-style operational purge (no volume wipe).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_DIR="${PLAY_REVIEW_COMPOSE_DIR:-$ROOT/cloud/play-review}"
ENV_FILE="${PLAY_REVIEW_ENV_FILE:-$COMPOSE_DIR/.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE" >&2
  exit 1
fi

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a

PLAY_REVIEW_URL="${PLAY_REVIEW_URL:-https://play-review.demo.vendiqo.ch}"
PLAY_REVIEW_URL="${PLAY_REVIEW_URL%/}"
CLOUD_API_BASE="${PLAY_REVIEW_CLOUD_API_BASE:-${CLOUD_BASE_URL:-https://api.vendiqo.ch}}"
CLOUD_API_BASE="${CLOUD_API_BASE%/}"

if [[ -z "${PLAY_REVIEW_CLEANUP_SECRET:-}" ]]; then
  echo "PLAY_REVIEW_CLEANUP_SECRET is required in $ENV_FILE" >&2
  exit 1
fi

echo "==> Pi operational purge (HOSTED_PI)"
curl -fsS -X POST "$PLAY_REVIEW_URL/v1/ops/purge-operational" \
  -H "Content-Type: application/json" \
  -H "X-Cleanup-Secret: ${PLAY_REVIEW_CLEANUP_SECRET}"
echo

if [[ -n "${PLAY_REVIEW_EVENT_ID:-}" && -n "${PLAY_REVIEW_CLOUD_TOKEN:-}" ]]; then
  echo "==> Cloud operational purge for event ${PLAY_REVIEW_EVENT_ID}"
  curl -fsS -X POST "${CLOUD_API_BASE}/events/${PLAY_REVIEW_EVENT_ID}/purge-operational" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${PLAY_REVIEW_CLOUD_TOKEN}"
  echo
else
  echo "==> Skipping cloud purge (set PLAY_REVIEW_EVENT_ID and PLAY_REVIEW_CLOUD_TOKEN to enable)"
fi

echo "Play review cleanup OK: $PLAY_REVIEW_URL"
