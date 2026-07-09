#!/bin/bash
# Resolve absolute path to npm for Gradle/Android Studio (GUI PATH often omits Homebrew).
# Prints the path to stdout. Exits 1 with a clear message if not found.
set -euo pipefail

find_npm_on_path() {
  command -v npm 2>/dev/null || true
}

candidate_dirs() {
  if [[ -n "${NPM_RESOLVE_CANDIDATE_DIRS+x}" ]]; then
    # Test hook: space-separated dirs (may be empty to disable system fallbacks).
    # shellcheck disable=SC2206
    local dirs=( ${NPM_RESOLVE_CANDIDATE_DIRS:-} )
    printf '%s\n' "${dirs[@]+"${dirs[@]}"}"
    return
  fi
  printf '%s\n' \
    /opt/homebrew/bin \
    /usr/local/bin \
    "$HOME/.local/bin" \
    "$HOME/.nvm/current/bin" \
    "$HOME/.fnm/current/bin" \
    "$HOME/.volta/bin" \
    "$HOME/.asdf/shims"
}

resolve_npm() {
  local from_path
  from_path="$(find_npm_on_path)"
  if [[ -n "$from_path" && -x "$from_path" ]]; then
    # Keep the wrapper path (do not realpath: Homebrew npm → npm-cli.js).
    echo "$from_path"
    return 0
  fi

  local dir
  while IFS= read -r dir; do
    [[ -z "$dir" ]] && continue
    if [[ -x "$dir/npm" ]]; then
      echo "$dir/npm"
      return 0
    fi
  done < <(candidate_dirs)

  # nvm without "current" symlink: newest installed node/*/bin/npm
  local nvm_npm
  nvm_npm="$(ls -1d "$HOME"/.nvm/versions/node/*/bin/npm 2>/dev/null | tail -n 1 || true)"
  if [[ -n "$nvm_npm" && -x "$nvm_npm" ]]; then
    echo "$nvm_npm"
    return 0
  fi

  return 1
}

main() {
  local npm_path
  if ! npm_path="$(resolve_npm)"; then
    cat >&2 <<'EOF'
npm not found.

Android Studio / Gradle often run with a minimal PATH that does not include
Homebrew (/opt/homebrew/bin) or nvm. Install Node.js, or ensure npm is
available at one of:
  /opt/homebrew/bin/npm
  /usr/local/bin/npm
  ~/.nvm/.../bin/npm

Workaround: quit Android Studio and open it from a terminal where `npm` works:
  open -a "Android Studio"
EOF
    exit 1
  fi
  echo "$npm_path"
}

main "$@"
