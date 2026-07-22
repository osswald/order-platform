#!/usr/bin/env bash
# Deploy persistent Play review Pi: pull images, reset demo DB, sync config, health check.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_DIR="${PLAY_REVIEW_COMPOSE_DIR:-$ROOT/cloud/play-review}"
COMPOSE_PROJECT_NAME="${PLAY_REVIEW_COMPOSE_PROJECT:-play-review}"
ENV_FILE="${PLAY_REVIEW_ENV_FILE:-$COMPOSE_DIR/.env}"
ANDROID_WEBVIEW_ORIGIN="${PLAY_REVIEW_ANDROID_ORIGIN:-https://appassets.androidplatform.net}"

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

check_health_json() {
  local url="$1"
  local tmp headers ctype acao
  tmp="$(mktemp)"
  headers="$(mktemp)"
  if ! curl -fsS -D "$headers" -o "$tmp" -H "Origin: ${ANDROID_WEBVIEW_ORIGIN}" "$url"; then
    rm -f "$tmp" "$headers"
    return 1
  fi
  ctype="$(tr -d '\r' <"$headers" | awk -F': ' 'tolower($1)=="content-type" {print tolower($2); exit}')"
  acao="$(tr -d '\r' <"$headers" | awk -F': ' 'tolower($1)=="access-control-allow-origin" {print $2; exit}')"
  if [[ "$ctype" != application/json* ]]; then
    echo "Expected application/json from $url, got: ${ctype:-<missing>}" >&2
    head -c 200 "$tmp" >&2 || true
    echo >&2
    rm -f "$tmp" "$headers"
    return 1
  fi
  body="$(cat "$tmp")"
  rm -f "$tmp" "$headers"
  if ! grep -Eq '"status"[[:space:]]*:[[:space:]]*"ok"' <<<"$body"; then
    echo "Health JSON missing status=ok from $url: $body" >&2
    return 1
  fi
  if [[ -z "$acao" ]]; then
    echo "Missing Access-Control-Allow-Origin for Origin=${ANDROID_WEBVIEW_ORIGIN} on $url" >&2
    return 1
  fi
  if [[ "$acao" != "*" && "$acao" != "$ANDROID_WEBVIEW_ORIGIN" ]]; then
    echo "Unexpected Access-Control-Allow-Origin='$acao' on $url" >&2
    return 1
  fi
  return 0
}

echo "==> Waiting for public JSON /health (with Android WebView CORS)"
deadline=$((SECONDS + 120))
ok=0
while (( SECONDS < deadline )); do
  if check_health_json "$PLAY_REVIEW_URL/health"; then
    ok=1
    break
  fi
  sleep 2
done
if (( ok != 1 )); then
  echo "Health check timed out for: $PLAY_REVIEW_URL/health (JSON + CORS required)" >&2
  exit 1
fi

echo "==> Sync pull (fresh bundle from cloud)"
curl -fsS -X POST "$PLAY_REVIEW_URL/v1/sync/pull" -H 'Content-Type: application/json'
echo

echo "==> Setup status"
curl -fsS "$PLAY_REVIEW_URL/v1/setup/status" || true
echo
echo "Play review deploy OK: $PLAY_REVIEW_URL"
