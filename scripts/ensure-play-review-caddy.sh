#!/usr/bin/env bash
# Write / refresh the Play review Caddy snippet and reload Caddy.
# The snippet lives in cloud/hosted-snippets (imported by cloud/Caddyfile).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SNIPPETS_DIR="${PLAY_REVIEW_CADDY_SNIPPETS_DIR:-$ROOT/cloud/hosted-snippets}"
CADDY_CONTAINER="${PLAY_REVIEW_CADDY_CONTAINER:-cloud-caddy-1}"
PLAY_REVIEW_HOST="${PLAY_REVIEW_HOST:-play-review.demo.vendiqo.ch}"
FRONTEND_FILTER="${PLAY_REVIEW_FRONTEND_FILTER:-name=play-review-pi-frontend}"

frontend="$(docker ps --format '{{.Names}}' --filter "$FRONTEND_FILTER" | head -n 1 || true)"
if [[ -z "$frontend" ]]; then
  echo "No running container matching filter '$FRONTEND_FILTER' (expected play-review-pi-frontend-*)." >&2
  echo "Start the play-review stack before ensuring the Caddy route." >&2
  exit 1
fi

mkdir -p "$SNIPPETS_DIR"
snippet="$SNIPPETS_DIR/play-review.caddy"
tmp="$(mktemp "$SNIPPETS_DIR/play-review.caddy.tmp.XXXXXX")"
cat >"$tmp" <<EOF
# Managed by scripts/ensure-play-review-caddy.sh — do not leave FRONTEND_CONTAINER placeholders.
${PLAY_REVIEW_HOST} {
	import security_headers
	reverse_proxy ${frontend}:80 {
		header_down -Server
	}
}
EOF
mv -f "$tmp" "$snippet"
echo "==> Wrote Caddy snippet $snippet -> ${frontend}:80"

echo "==> Reloading Caddy ($CADDY_CONTAINER)"
docker exec "$CADDY_CONTAINER" caddy reload --config /etc/caddy/Caddyfile
echo "Play review Caddy route OK: https://${PLAY_REVIEW_HOST}"
