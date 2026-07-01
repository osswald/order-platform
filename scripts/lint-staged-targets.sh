#!/usr/bin/env bash
# Shared helpers for mapping staged paths to lint targets (sourced by lint.sh).

mark_lint_targets_for_staged_path() {
  local f="$1"
  case "$f" in
    ruff.toml)
      run_ruff_cloud=true
      run_ruff_pi=true
      ;;
    eslint.config.js | package.json | package-lock.json)
      run_eslint_cloud=true
      run_eslint_pi=true
      ;;
    packages/frontend-shared/*)
      run_eslint_cloud=true
      run_eslint_pi=true
      ;;
    cloud/backend/*)
      run_ruff_cloud=true
      ;;
    pi/backend/*)
      run_ruff_pi=true
      ;;
    cloud/frontend/*)
      run_eslint_cloud=true
      ;;
    pi/frontend/*)
      run_eslint_pi=true
      ;;
  esac
}
