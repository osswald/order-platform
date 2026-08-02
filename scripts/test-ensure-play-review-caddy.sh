#!/usr/bin/env bash
# Unit tests for ensure-play-review-caddy.sh (no Docker / live VPS required).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENSURE="$ROOT/scripts/ensure-play-review-caddy.sh"
failures=0

assert_eq() {
  local label="$1"
  local expected="$2"
  local actual="$3"
  if [[ "$expected" != "$actual" ]]; then
    echo "FAIL: $label" >&2
    echo "  expected: $expected" >&2
    echo "  actual:   $actual" >&2
    failures=$((failures + 1))
  fi
}

assert_file_contains() {
  local label="$1"
  local file="$2"
  local pattern="$3"
  if ! grep -Eq -- "$pattern" "$file"; then
    echo "FAIL: $label" >&2
    echo "  expected /$pattern/ in $file" >&2
    failures=$((failures + 1))
  fi
}

assert_file_exists() {
  local label="$1"
  local file="$2"
  if [[ ! -f "$file" ]]; then
    echo "FAIL: $label" >&2
    echo "  missing file: $file" >&2
    failures=$((failures + 1))
  fi
}

assert_file_exists "ensure-play-review-caddy.sh exists" "$ENSURE"
assert_file_contains "ensure script is executable bash" "$ENSURE" '^#!/usr/bin/env bash'

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

# Fake docker: report a stable frontend container name; record reload invocations.
cat >"$tmpdir/docker" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "ps" ]]; then
  echo "play-review-pi-frontend-1"
  exit 0
fi
if [[ "${1:-}" == "exec" ]]; then
  printf '%s\n' "$*" >>"${DOCKER_LOG}"
  exit 0
fi
echo "unexpected docker args: $*" >&2
exit 1
EOF
chmod +x "$tmpdir/docker"

export PATH="$tmpdir:$PATH"
export DOCKER_LOG="$tmpdir/docker.log"
export PLAY_REVIEW_CADDY_SNIPPETS_DIR="$tmpdir/snippets"
export PLAY_REVIEW_CADDY_CONTAINER="cloud-caddy-1"
export PLAY_REVIEW_HOST="play-review.demo.vendiqo.ch"
: >"$DOCKER_LOG"

"$ENSURE"

snippet="$PLAY_REVIEW_CADDY_SNIPPETS_DIR/play-review.caddy"
assert_file_exists "writes play-review.caddy snippet" "$snippet"
assert_file_contains "snippet uses review host" "$snippet" \
  '^play-review\.demo\.vendiqo\.ch \{'
assert_file_contains "snippet proxies to discovered frontend container" "$snippet" \
  'reverse_proxy play-review-pi-frontend-1:80'
assert_file_contains "snippet imports security_headers" "$snippet" \
  'import security_headers'

reload_lines="$(wc -l <"$DOCKER_LOG" | tr -d ' ')"
assert_eq "reloads Caddy once" "1" "$reload_lines"
assert_file_contains "reload uses configured Caddy container" "$DOCKER_LOG" \
  'exec cloud-caddy-1 caddy reload --config /etc/caddy/Caddyfile'

# Missing frontend container should fail clearly (do not clobber snippet with empty proxy).
cat >"$tmpdir/docker" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "ps" ]]; then
  exit 0
fi
echo "unexpected docker args: $*" >&2
exit 1
EOF
chmod +x "$tmpdir/docker"
if "$ENSURE" >"$tmpdir/out" 2>"$tmpdir/err"; then
  echo "FAIL: ensure should fail when frontend container is missing" >&2
  failures=$((failures + 1))
else
  assert_file_contains "missing frontend error mentions play-review" "$tmpdir/err" \
    'play-review-pi-frontend'
fi

# Tracked template in repo must not leave FRONTEND_CONTAINER placeholder.
tracked="$ROOT/cloud/hosted-snippets/play-review.caddy"
assert_file_exists "tracked hosted-snippets/play-review.caddy exists" "$tracked"
assert_file_contains "tracked snippet uses concrete frontend container" "$tracked" \
  'reverse_proxy play-review-pi-frontend-1:80'
assert_file_lacks_placeholder() {
  if grep -Eq 'FRONTEND_CONTAINER' "$tracked"; then
    echo "FAIL: tracked snippet still has FRONTEND_CONTAINER placeholder" >&2
    failures=$((failures + 1))
  fi
}
assert_file_lacks_placeholder

if [[ $failures -gt 0 ]]; then
  echo "$failures test(s) failed." >&2
  exit 1
fi

echo "All ensure-play-review-caddy tests passed."
