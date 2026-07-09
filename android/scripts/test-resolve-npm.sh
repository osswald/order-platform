#!/bin/bash
# Unit tests for android/scripts/resolve-npm.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RESOLVE="$ROOT/android/scripts/resolve-npm.sh"
failures=0

assert_ok_executable() {
  local label="$1"
  local out="$2"
  if [[ ! -x "$out" ]]; then
    echo "FAIL: $label — expected executable path, got: $out" >&2
    failures=$((failures + 1))
    return
  fi
  local base
  base="$(basename "$out")"
  if [[ "$base" != "npm" && "$base" != "npm.cmd" ]]; then
    echo "FAIL: $label — expected basename npm, got: $base ($out)" >&2
    failures=$((failures + 1))
  fi
}

# Happy path: real environment should resolve npm.
out="$("$RESOLVE")"
assert_ok_executable "default PATH" "$out"

# GUI-like PATH (common when Android Studio launches Gradle): no Homebrew/nvm.
# Still must find Homebrew (Apple Silicon) or /usr/local (Intel) if present.
if [[ -x /opt/homebrew/bin/npm || -x /usr/local/bin/npm ]]; then
  out="$(PATH="/usr/bin:/bin:/usr/sbin:/sbin" "$RESOLVE")"
  assert_ok_executable "minimal macOS PATH" "$out"
fi

# Failure path: no PATH hit and no system candidate dirs.
# Keep /bin so #!/bin/bash / command -v still work; exclude dirs that contain npm.
tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT
empty_path="/usr/bin:/bin"
if PATH="$empty_path" HOME="$tmpdir" NPM_RESOLVE_CANDIDATE_DIRS= "$RESOLVE" >/dev/null 2>"$tmpdir/err"; then
  echo "FAIL: expected resolve-npm.sh to fail when npm is missing" >&2
  failures=$((failures + 1))
else
  if ! grep -qi "npm not found" "$tmpdir/err"; then
    echo "FAIL: expected 'npm not found' in stderr, got:" >&2
    cat "$tmpdir/err" >&2
    failures=$((failures + 1))
  fi
fi

# Explicit candidate dir wins when PATH has no npm.
fake_bin="$tmpdir/bin"
mkdir -p "$fake_bin"
# Minimal executable stub named npm.
printf '#!/bin/sh\nexit 0\n' >"$fake_bin/npm"
chmod +x "$fake_bin/npm"
out="$(PATH="$empty_path" HOME="$tmpdir" NPM_RESOLVE_CANDIDATE_DIRS="$fake_bin" "$RESOLVE")"
assert_ok_executable "candidate dir" "$out"
if [[ "$out" != "$fake_bin/npm" ]]; then
  echo "FAIL: candidate dir — expected $fake_bin/npm, got: $out" >&2
  failures=$((failures + 1))
fi

if [[ $failures -gt 0 ]]; then
  echo "$failures test(s) failed." >&2
  exit 1
fi

echo "All resolve-npm tests passed."
