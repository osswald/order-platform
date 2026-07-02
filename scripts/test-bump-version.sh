#!/usr/bin/env bash
# Unit tests for scripts/bump-version.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUMP="$ROOT/scripts/bump-version.sh"

failures=0

assert_eq() {
  local label="$1"
  local want="$2"
  local got="$3"
  if [[ "$want" != "$got" ]]; then
    echo "FAIL: $label" >&2
    echo "  expected: $want" >&2
    echo "  got:      $got" >&2
    failures=$((failures + 1))
  fi
}

assert_exit_nonzero() {
  local label="$1"
  shift
  if "$@" >/dev/null 2>&1; then
    echo "FAIL: $label (expected non-zero exit)" >&2
    failures=$((failures + 1))
  fi
}

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

write_version() {
  printf '%s\n' "$1" > "$tmpdir/VERSION"
}

run_bump() {
  VERSION_FILE="$tmpdir/VERSION" "$BUMP" "$@"
}

# patch / minor / major from file
write_version "1.1.2"
assert_eq "patch bump" "1.1.3" "$(run_bump patch --print-only)"
assert_eq "patch writes file" "1.1.3" "$(run_bump patch)"
assert_eq "patch file contents" "1.1.3" "$(tr -d '[:space:]' < "$tmpdir/VERSION")"

write_version "1.1.2"
assert_eq "minor bump" "1.2.0" "$(run_bump minor --print-only)"
run_bump minor >/dev/null
assert_eq "minor file contents" "1.2.0" "$(tr -d '[:space:]' < "$tmpdir/VERSION")"

write_version "1.1.2"
assert_eq "major bump" "2.0.0" "$(run_bump major --print-only)"
run_bump major >/dev/null
assert_eq "major file contents" "2.0.0" "$(tr -d '[:space:]' < "$tmpdir/VERSION")"

# --from without reading file
write_version "9.9.9"
assert_eq "from patch" "1.1.3" "$(run_bump patch --from 1.1.2 --print-only)"
assert_eq "from leaves file" "9.9.9" "$(tr -d '[:space:]' < "$tmpdir/VERSION")"
assert_eq "from minor" "1.2.0" "$(run_bump minor --from 1.1.2 --print-only)"
assert_eq "from major" "2.0.0" "$(run_bump major --from 1.1.2 --print-only)"

# trims whitespace
write_version "  3.4.5  "
run_bump patch >/dev/null
assert_eq "trim whitespace" "3.4.6" "$(tr -d '[:space:]' < "$tmpdir/VERSION")"

# errors
assert_exit_nonzero "invalid part" run_bump invalid --print-only
assert_exit_nonzero "malformed version" run_bump patch --from not-a-version --print-only
touch "$tmpdir/empty"
assert_exit_nonzero "empty version file" env VERSION_FILE="$tmpdir/empty" "$BUMP" patch --print-only

if [[ $failures -gt 0 ]]; then
  echo "$failures test(s) failed." >&2
  exit 1
fi

echo "All bump-version tests passed."
