#!/usr/bin/env bash
# One-time GitHub setup for label-gated releases (labels + optional branch check hint).
set -euo pipefail

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI is required: https://cli.github.com/" >&2
  exit 1
fi

repo="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
echo "Configuring release labels for $repo"

create_label() {
  local name="$1"
  local color="$2"
  local description="$3"
  if gh label list --json name -q '.[].name' | grep -Fxq "$name"; then
    echo "Label exists: $name"
  else
    gh label create "$name" --color "$color" --description "$description"
    echo "Created label: $name"
  fi
}

create_label "release:patch" "0E8A16" "Patch release on merge (bugfixes)"
create_label "release:minor" "1D76DB" "Minor release on merge (features)"
create_label "release:major" "B60205" "Major release on merge (breaking changes)"

cat <<EOF

Done. Manual steps in GitHub UI:

1. Settings → Actions → General → Workflow permissions → Read and write
2. Settings → Branches → main protection → Require status check: PR gate / gate
   (enable after the release workflows are merged to main)

See docs/RELEASE.md for the full workflow.
EOF
