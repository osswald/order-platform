#!/usr/bin/env bash
# npm wrapper: unsets deprecated npm_config_devdir (set by some IDE/sandbox environments).
set -euo pipefail
unset npm_config_devdir 2>/dev/null || true
exec npm "$@"
