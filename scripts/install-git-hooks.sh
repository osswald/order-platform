#!/usr/bin/env bash
# Point this repo at tracked git hooks under .githooks/
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

chmod +x .githooks/pre-commit scripts/lint.sh scripts/install-git-hooks.sh
git config core.hooksPath .githooks

echo "Installed git hooks (core.hooksPath=.githooks)."
echo "Pre-commit runs ./scripts/lint.sh --staged (Ruff + ESLint for affected areas)."
