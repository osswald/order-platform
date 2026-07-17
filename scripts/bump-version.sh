#!/usr/bin/env bash
# Bump the repo VERSION file (semver X.Y.Z).
# Usage: bump-version.sh patch|minor|major [--from X.Y.Z] [--print-only]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION_FILE="${VERSION_FILE:-$ROOT/VERSION}"

SEMVER_RE='^[0-9]+\.[0-9]+\.[0-9]+$'

usage() {
  echo "Usage: bump-version.sh patch|minor|major [--from X.Y.Z] [--print-only]" >&2
  exit 1
}

validate_version() {
  local version="$1"
  if [[ ! "$version" =~ $SEMVER_RE ]]; then
    echo "Invalid semver: $version (expected X.Y.Z)" >&2
    exit 1
  fi
}

bump_version() {
  local version="$1"
  local part="$2"
  local major minor patch
  IFS=. read -r major minor patch <<< "$version"
  case "$part" in
    patch) patch=$((patch + 1)) ;;
    minor)
      minor=$((minor + 1))
      patch=0
      ;;
    major)
      major=$((major + 1))
      minor=0
      patch=0
      ;;
    *)
      echo "Invalid bump type: $part (expected patch, minor, or major)" >&2
      exit 1
      ;;
  esac
  echo "${major}.${minor}.${patch}"
}

part=""
base_from=""
print_only=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    patch|minor|major)
      part="$1"
      shift
      ;;
    --from)
      [[ $# -ge 2 ]] || usage
      base_from="$2"
      shift 2
      ;;
    --print-only)
      print_only=true
      shift
      ;;
    -h|--help)
      usage
      ;;
    *)
      usage
      ;;
  esac
done

[[ -n "$part" ]] || usage

if [[ -n "$base_from" ]]; then
  current="$(echo "$base_from" | tr -d '[:space:]')"
else
  if [[ ! -f "$VERSION_FILE" ]]; then
    echo "VERSION file not found: $VERSION_FILE" >&2
    exit 1
  fi
  current="$(tr -d '[:space:]' < "$VERSION_FILE")"
  if [[ -z "$current" ]]; then
    echo "VERSION file is empty: $VERSION_FILE" >&2
    exit 1
  fi
fi

validate_version "$current"
next="$(bump_version "$current" "$part")"

if [[ "$print_only" == true ]]; then
  echo "$next"
  exit 0
fi

printf '%s\n' "$next" > "$VERSION_FILE"
echo "$next"
