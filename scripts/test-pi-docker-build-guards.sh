#!/usr/bin/env bash
# Static guards for Pi Docker image builds.
# Catches regressions that previously shipped empty arm64 venv entrypoints
# when CI built linux/arm64 under QEMU emulation.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCKERFILE="$ROOT/pi/backend/Dockerfile"
WORKFLOW="$ROOT/.github/workflows/pi-docker.yml"

failures=0

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

assert_file_lacks() {
  local label="$1"
  local file="$2"
  local pattern="$3"
  if grep -Eq -- "$pattern" "$file"; then
    echo "FAIL: $label" >&2
    echo "  did not expect /$pattern/ in $file" >&2
    failures=$((failures + 1))
  fi
}

assert_file_contains "Dockerfile uses UV_LINK_MODE=copy" "$DOCKERFILE" \
  '^ENV UV_LINK_MODE=copy$'
assert_file_contains "Dockerfile verifies uvicorn entrypoint is non-empty" "$DOCKERFILE" \
  'test -s /repo/pi/backend/\.venv/bin/uvicorn'
assert_file_contains "Dockerfile verifies uvicorn imports" "$DOCKERFILE" \
  'import uvicorn'
assert_file_contains "Dockerfile starts via python -m uvicorn" "$DOCKERFILE" \
  'CMD \["python", "-m", "uvicorn"'

assert_file_contains "workflow builds on ubuntu-24.04-arm" "$WORKFLOW" \
  'ubuntu-24\.04-arm'
assert_file_contains "workflow builds on ubuntu-latest for amd64" "$WORKFLOW" \
  'ubuntu-latest'
assert_file_contains "workflow uses push-by-digest for per-arch builds" "$WORKFLOW" \
  'push-by-digest=true'
assert_file_contains "workflow merges manifests with imagetools" "$WORKFLOW" \
  'buildx imagetools create'
assert_file_lacks "workflow does not use QEMU for Pi images" "$WORKFLOW" \
  'setup-qemu-action'
assert_file_lacks "workflow does not build both platforms in one QEMU job" "$WORKFLOW" \
  'platforms: linux/amd64,linux/arm64'

if [[ $failures -gt 0 ]]; then
  echo "$failures test(s) failed." >&2
  exit 1
fi

echo "All pi docker build guard tests passed."
