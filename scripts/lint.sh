#!/usr/bin/env bash
# Run Ruff and ESLint checks (same scope as .github/workflows/lint.yml).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

STAGED_ONLY=false
if [[ "${1:-}" == "--staged" ]]; then
  STAGED_ONLY=true
fi

run_ruff_cloud=false
run_ruff_pi=false
run_eslint_cloud=false
run_eslint_pi=false

# shellcheck source=scripts/lint-staged-targets.sh
source "$ROOT/scripts/lint-staged-targets.sh"

if $STAGED_ONLY; then
  staged="$(git diff --cached --name-only --diff-filter=ACM)"
  if [[ -z "$staged" ]]; then
    exit 0
  fi
  while IFS= read -r f; do
    [[ -z "$f" ]] && continue
    mark_lint_targets_for_staged_path "$f"
  done <<< "$staged"
else
  run_ruff_cloud=true
  run_ruff_pi=true
  run_eslint_cloud=true
  run_eslint_pi=true
fi

if ! $run_ruff_cloud && ! $run_ruff_pi && ! $run_eslint_cloud && ! $run_eslint_pi; then
  exit 0
fi

ruff_cmd() {
  if command -v uvx >/dev/null 2>&1; then
    uvx ruff "$@"
  elif command -v ruff >/dev/null 2>&1; then
    ruff "$@"
  elif python3 -m ruff --version >/dev/null 2>&1; then
    python3 -m ruff "$@"
  else
    echo "error: ruff not found. Install uv (https://docs.astral.sh/uv/): curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
    exit 1
  fi
}

ensure_root_node_modules() {
  if [[ ! -d node_modules ]]; then
    echo "error: run './scripts/npm.sh ci' at the repo root before linting frontends." >&2
    exit 1
  fi
}

ensure_frontend_node_modules() {
  local frontend="$1"
  if [[ ! -d "$frontend/node_modules" ]]; then
    echo "error: run './scripts/npm.sh ci' in $frontend before linting." >&2
    exit 1
  fi
}

run_eslint() {
  local frontend="$1"
  ensure_root_node_modules
  ensure_frontend_node_modules "$frontend"
  npx eslint --config eslint.config.js "$frontend/src" packages/frontend-shared/src
}

if $run_ruff_cloud; then
  echo "Ruff (cloud)..."
  ruff_cmd check cloud/backend/app cloud/backend/tests
fi

if $run_ruff_pi; then
  echo "Ruff (pi)..."
  ruff_cmd check pi/backend/app pi/backend/tests
fi

if $run_eslint_cloud; then
  echo "ESLint (cloud frontend)..."
  run_eslint cloud/frontend
fi

if $run_eslint_pi; then
  echo "ESLint (pi frontend)..."
  run_eslint pi/frontend
fi

echo "Lint passed."
