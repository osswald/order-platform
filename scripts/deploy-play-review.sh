#!/usr/bin/env bash
# Deploy persistent Play review Pi: pull images, reset demo DB, sync config, health check.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_DIR="${PLAY_REVIEW_COMPOSE_DIR:-$ROOT/cloud/play-review}"
COMPOSE_PROJECT_NAME="${PLAY_REVIEW_COMPOSE_PROJECT:-play-review}"
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

echo "==> Pulling images"
docker compose -f "$COMPOSE_DIR/docker-compose.yml" --env-file "$ENV_FILE" -p "$COMPOSE_PROJECT_NAME" pull

echo "==> Stopping stack and wiping pi-data (demo reset)"
docker compose -f "$COMPOSE_DIR/docker-compose.yml" --env-file "$ENV_FILE" -p "$COMPOSE_PROJECT_NAME" down -v --remove-orphans

echo "==> Starting stack"
docker compose -f "$COMPOSE_DIR/docker-compose.yml" --env-file "$ENV_FILE" -p "$COMPOSE_PROJECT_NAME" up -d --wait

# Prefer /health (newer Pi frontend nginx); fall back to /v1/setup/status.
HEALTH_PATHS=("$PLAY_REVIEW_URL/health" "$PLAY_REVIEW_URL/v1/setup/status")

echo "==> Waiting for public health endpoint"
deadline=$((SECONDS + 120))
ok=0
while (( SECONDS < deadline )); do
  for url in "${HEALTH_PATHS[@]}"; do
    if curl -fsS "$url" >/dev/null 2>&1; then
      ok=1
      break 2
    fi
  done
  sleep 2
done
if (( ok != 1 )); then
  echo "Health check timed out for: ${HEALTH_PATHS[*]}" >&2
  exit 1
fi

echo "==> Sync pull (fresh bundle from cloud)"
curl -fsS -X POST "$PLAY_REVIEW_URL/v1/sync/pull" -H 'Content-Type: application/json'
echo

echo "==> Setup status"
curl -fsS "$PLAY_REVIEW_URL/v1/setup/status" || true
echo
echo "Play review deploy OK: $PLAY_REVIEW_URL"
