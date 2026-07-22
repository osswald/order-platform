#!/usr/bin/env bash
# Static guards for Play review SSH workflows.
# The VPS git is older than 2.29 and rejects `git fetch --ff-only`
# (that flag exists for merge/pull, not fetch, on older git).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_WF="$ROOT/.github/workflows/play-review-deploy.yml"
CLEANUP_WF="$ROOT/.github/workflows/play-review-cleanup.yml"

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

for wf in "$DEPLOY_WF" "$CLEANUP_WF"; do
  name="$(basename "$wf")"
  assert_file_lacks "$name does not use git fetch --ff-only (unsupported on VPS git)" "$wf" \
    '[[:space:]]git fetch --ff-only'
  assert_file_contains "$name fetches origin main without --ff-only" "$wf" \
    '[[:space:]]git fetch origin main'
  assert_file_contains "$name merges with --ff-only" "$wf" \
    '[[:space:]]git merge --ff-only origin/main'
done

if [[ $failures -gt 0 ]]; then
  echo "$failures test(s) failed." >&2
  exit 1
fi

echo "All play-review workflow guard tests passed."
