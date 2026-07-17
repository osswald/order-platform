#!/usr/bin/env bash
# Unit tests for staged-path -> lint target mapping.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/lint-staged-targets.sh
source "$ROOT/scripts/lint-staged-targets.sh"

failures=0

assert_flags() {
  local label="$1"
  local want_ruff_cloud="$2"
  local want_ruff_pi="$3"
  local want_eslint_cloud="$4"
  local want_eslint_pi="$5"

  if [[ "$run_ruff_cloud" != "$want_ruff_cloud" ]] \
    || [[ "$run_ruff_pi" != "$want_ruff_pi" ]] \
    || [[ "$run_eslint_cloud" != "$want_eslint_cloud" ]] \
    || [[ "$run_eslint_pi" != "$want_eslint_pi" ]]; then
    echo "FAIL: $label" >&2
    echo "  expected ruff_cloud=$want_ruff_cloud ruff_pi=$want_ruff_pi eslint_cloud=$want_eslint_cloud eslint_pi=$want_eslint_pi" >&2
    echo "  got      ruff_cloud=$run_ruff_cloud ruff_pi=$run_ruff_pi eslint_cloud=$run_eslint_cloud eslint_pi=$run_eslint_pi" >&2
    failures=$((failures + 1))
  fi
}

check_path() {
  local path="$1"
  local want_ruff_cloud="$2"
  local want_ruff_pi="$3"
  local want_eslint_cloud="$4"
  local want_eslint_pi="$5"
  run_ruff_cloud=false
  run_ruff_pi=false
  run_eslint_cloud=false
  run_eslint_pi=false
  mark_lint_targets_for_staged_path "$path"
  assert_flags "$path" "$want_ruff_cloud" "$want_ruff_pi" "$want_eslint_cloud" "$want_eslint_pi"
}

check_path ruff.toml true true false false
check_path eslint.config.js false false true true
check_path package.json false false true true
check_path packages/frontend-shared/src/foo.ts false false true true
check_path cloud/backend/app/foo.py true false false false
check_path pi/backend/app/foo.py false true false false
check_path cloud/frontend/src/App.vue false false true false
check_path pi/frontend/src/App.vue false false false true

if [[ $failures -gt 0 ]]; then
  echo "$failures test(s) failed." >&2
  exit 1
fi

echo "All lint staged-target tests passed."
