#!/usr/bin/env bash
# Static guards for Play review SSH workflows.
# The VPS git is older than 2.29 and rejects `git fetch --ff-only`
# (that flag exists for merge/pull, not fetch, on older git).
# The deploy workflow must not use pull_request with a skipped deploy job
# (that shows as success while never deploying).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_WF="$ROOT/.github/workflows/play-review-deploy.yml"
CLEANUP_WF="$ROOT/.github/workflows/play-review-cleanup.yml"
GUARDS_WF="$ROOT/.github/workflows/play-review-guards.yml"

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

assert_file_exists() {
  local label="$1"
  local file="$2"
  if [[ ! -f "$file" ]]; then
    echo "FAIL: $label" >&2
    echo "  missing file: $file" >&2
    failures=$((failures + 1))
  fi
}

for wf in "$DEPLOY_WF" "$CLEANUP_WF"; do
  name="$(basename "$wf")"
  assert_file_lacks "$name does not use git fetch --ff-only (unsupported on VPS git)" "$wf" \
    '[[:space:]]git fetch --ff-only'
  assert_file_contains "$name fetches origin main without --ff-only" "$wf" \
    '[[:space:]]git fetch origin main'
  # Dirty tracked files on the VPS block merge; reset before clean/merge.
  assert_file_contains "$name resets hard before merge (discard local tracked edits)" "$wf" \
    '[[:space:]]git reset --hard HEAD'
  assert_file_contains "$name merges with --ff-only" "$wf" \
    '[[:space:]]git merge --ff-only origin/main'
  # Untracked hosted Caddy snippets must survive clean; deleting play-review.caddy
  # leaves Caddy without a TLS site block after the next reload.
  assert_file_contains "$name git clean excludes hosted-snippets" "$wf" \
    'git clean -fd -e cloud/hosted-snippets'
  # reset must run before merge so dirty edge.py (etc.) cannot abort sync.
  if ! awk '
    /git reset --hard HEAD/ { reset=1 }
    /git merge --ff-only origin\/main/ { merge=1; if (!reset) exit 1 }
    END { if (!reset || !merge) exit 1 }
  ' "$wf"; then
    echo "FAIL: $name must run git reset --hard HEAD before git merge --ff-only" >&2
    failures=$((failures + 1))
  fi
done

assert_file_lacks "play-review-deploy.yml is not triggered by pull_request" "$DEPLOY_WF" \
  '^[[:space:]]*pull_request:'
assert_file_contains "play-review-deploy.yml supports workflow_dispatch" "$DEPLOY_WF" \
  '^[[:space:]]*workflow_dispatch:'
assert_file_contains "play-review-deploy.yml runs SSH deploy action" "$DEPLOY_WF" \
  'appleboy/ssh-action@'
assert_file_contains "play-review-deploy.yml runs workflow guards before deploy" "$DEPLOY_WF" \
  'test-play-review-workflow-guards\.sh'
assert_file_lacks "play-review-deploy.yml does not skip deploy on pull_request" "$DEPLOY_WF" \
  'Skip SSH on PRs'

assert_file_exists "PR guard workflow exists" "$GUARDS_WF"
assert_file_contains "play-review-guards.yml triggers on pull_request" "$GUARDS_WF" \
  '^[[:space:]]*pull_request:'
assert_file_contains "play-review-guards.yml runs workflow guards" "$GUARDS_WF" \
  'test-play-review-workflow-guards\.sh'
assert_file_lacks "play-review-guards.yml does not SSH deploy" "$GUARDS_WF" \
  'appleboy/ssh-action@'

DEPLOY_SH="$ROOT/scripts/deploy-play-review.sh"
CLEANUP_SH="$ROOT/scripts/cleanup-play-review.sh"
ENSURE_SH="$ROOT/scripts/ensure-play-review-caddy.sh"
assert_file_exists "ensure-play-review-caddy.sh exists" "$ENSURE_SH"
assert_file_contains "deploy ensures Caddy route after stack up" "$DEPLOY_SH" \
  'ensure-play-review-caddy\.sh'
assert_file_contains "cleanup ensures Caddy route before purge" "$CLEANUP_SH" \
  'ensure-play-review-caddy\.sh'
assert_file_exists "tracked play-review Caddy snippet exists" \
  "$ROOT/cloud/hosted-snippets/play-review.caddy"

if [[ $failures -gt 0 ]]; then
  echo "$failures test(s) failed." >&2
  exit 1
fi

echo "All play-review workflow guard tests passed."
