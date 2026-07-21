#!/usr/bin/env bash
# Minimize-outage OTA for Vendiqo Pi edge containers.
# Invoked by vendiqo-pi-update.service (timer + OnBootSec=5min).
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/vendiqo/pi}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
OTA_STATE_HOST_DIR="${OTA_STATE_HOST_DIR:-${APP_DIR}/ota-state}"
FREEZE_FILE="${FREEZE_FILE:-${OTA_STATE_HOST_DIR}/freeze}"
BLACKLIST_FILE="${BLACKLIST_FILE:-${OTA_STATE_HOST_DIR}/blacklist}"
OTA_MIN_FREE_BYTES="${OTA_MIN_FREE_BYTES:-2147483648}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1/health}"
HEALTH_TIMEOUT_SEC="${HEALTH_TIMEOUT_SEC:-90}"
PREAPPLY_TIMEOUT_SEC="${PREAPPLY_TIMEOUT_SEC:-60}"
COMPOSE=(docker compose -f "$COMPOSE_FILE")

log() { echo "[pi-ota] $*"; }

load_env() {
  if [[ -f "${APP_DIR}/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "${APP_DIR}/.env"
    set +a
  fi
  OTA_STATE_HOST_DIR="${OTA_STATE_HOST_DIR:-${APP_DIR}/ota-state}"
  FREEZE_FILE="${FREEZE_FILE:-${OTA_STATE_HOST_DIR}/freeze}"
  BLACKLIST_FILE="${BLACKLIST_FILE:-${OTA_STATE_HOST_DIR}/blacklist}"
  OTA_MIN_FREE_BYTES="${OTA_MIN_FREE_BYTES:-2147483648}"
  FORCE_UPDATE="${FORCE_UPDATE:-0}"
}

force_update_enabled() {
  local v
  v="$(echo "${FORCE_UPDATE:-0}" | tr '[:upper:]' '[:lower:]')"
  [[ "$v" == "1" || "$v" == "true" || "$v" == "yes" ]]
}

freeze_active() {
  [[ -f "$FREEZE_FILE" ]] || return 1
  local v
  v="$(tr -d '[:space:]' <"$FREEZE_FILE" || true)"
  [[ "$v" == "1" || "$v" == "true" || "$v" == "yes" ]]
}

ensure_state_dir() {
  mkdir -p "$OTA_STATE_HOST_DIR"
}

is_blacklisted() {
  local digest="$1"
  [[ -n "$digest" ]] || return 1
  [[ -f "$BLACKLIST_FILE" ]] || return 1
  grep -Fxq "$digest" "$BLACKLIST_FILE"
}

blacklist_digest() {
  local digest="$1"
  [[ -n "$digest" ]] || return 0
  ensure_state_dir
  touch "$BLACKLIST_FILE"
  if ! grep -Fxq "$digest" "$BLACKLIST_FILE"; then
    echo "$digest" >>"$BLACKLIST_FILE"
    log "blacklisted digest $digest"
  fi
}

dangling_prune() {
  log "pruning dangling images"
  docker image prune -f || log "warning: image prune failed (non-fatal)"
}

docker_root_path() {
  local root
  root="$(docker info -f '{{.DockerRootDir}}' 2>/dev/null || true)"
  if [[ -n "$root" && -d "$root" ]]; then
    echo "$root"
    return 0
  fi
  if [[ -d /var/lib/docker ]]; then
    echo /var/lib/docker
    return 0
  fi
  echo /
}

free_bytes() {
  local path
  path="$(docker_root_path)"
  df -PB1 "$path" | awk 'NR==2 {print $4}'
}

ensure_free_space() {
  local free
  free="$(free_bytes)"
  if [[ -z "$free" ]]; then
    log "warning: could not determine free space; continuing"
    return 0
  fi
  if (( free >= OTA_MIN_FREE_BYTES )); then
    log "free space ${free} bytes (min ${OTA_MIN_FREE_BYTES})"
    return 0
  fi
  log "free space ${free} below min ${OTA_MIN_FREE_BYTES}; pruning dangling images"
  dangling_prune
  free="$(free_bytes)"
  if (( free >= OTA_MIN_FREE_BYTES )); then
    log "free space recovered to ${free} bytes after prune"
    return 0
  fi
  log "still only ${free} bytes free; skipping pull/apply"
  return 1
}

image_id() {
  local ref="$1"
  docker image inspect --format '{{.Id}}' "$ref" 2>/dev/null || true
}

running_image_id() {
  local service="$1"
  local cid
  cid="$("${COMPOSE[@]}" ps -q "$service" 2>/dev/null || true)"
  [[ -n "$cid" ]] || return 0
  docker inspect --format '{{.Image}}' "$cid" 2>/dev/null || true
}

wait_http_ok() {
  local url="$1"
  local timeout="$2"
  local start now
  start="$(date +%s)"
  while true; do
    if curl -fsS --max-time 5 "$url" >/dev/null 2>&1; then
      return 0
    fi
    now="$(date +%s)"
    if (( now - start >= timeout )); then
      return 1
    fi
    sleep 2
  done
}

preapply_backend_health() {
  local image="$1"
  local name="vendiqo-ota-probe-be-$$"
  local ok=0
  docker rm -f "$name" >/dev/null 2>&1 || true
  if ! docker run -d --rm --name "$name" -p 127.0.0.1:18080:8000 \
    -e DATABASE_URL="sqlite:////tmp/ota-probe.db" \
    -e SYNC_ENABLED=0 \
    "$image" >/dev/null; then
    log "pre-apply: failed to start backend probe container (infra); will retry later"
    return 2
  fi
  if wait_http_ok "http://127.0.0.1:18080/health" "$PREAPPLY_TIMEOUT_SEC"; then
    ok=1
  fi
  docker rm -f "$name" >/dev/null 2>&1 || true
  if [[ "$ok" -eq 1 ]]; then
    return 0
  fi
  return 1
}

preapply_frontend_health() {
  local image="$1"
  local name="vendiqo-ota-probe-fe-$$"
  local ok=0
  docker rm -f "$name" >/dev/null 2>&1 || true
  if ! docker run -d --rm --name "$name" -p 127.0.0.1:18081:80 "$image" >/dev/null; then
    log "pre-apply: failed to start frontend probe container (infra); will retry later"
    return 2
  fi
  if wait_http_ok "http://127.0.0.1:18081/" "$PREAPPLY_TIMEOUT_SEC"; then
    ok=1
  fi
  docker rm -f "$name" >/dev/null 2>&1 || true
  if [[ "$ok" -eq 1 ]]; then
    return 0
  fi
  return 1
}

compose_up() {
  "${COMPOSE[@]}" up -d
}

apply_with_images() {
  local be="$1"
  local fe="$2"
  PI_BACKEND_IMAGE="$be" PI_FRONTEND_IMAGE="$fe" "${COMPOSE[@]}" up -d
}

run_self_test() {
  local tmp
  tmp="$(mktemp -d)"
  # shellcheck disable=SC2064
  trap "rm -rf '$tmp'" EXIT
  OTA_STATE_HOST_DIR="$tmp"
  FREEZE_FILE="$tmp/freeze"
  BLACKLIST_FILE="$tmp/blacklist"
  ensure_state_dir

  echo "0" >"$FREEZE_FILE"
  freeze_active && { echo "fail: freeze 0 should be inactive"; exit 1; }
  echo "1" >"$FREEZE_FILE"
  freeze_active || { echo "fail: freeze 1 should be active"; exit 1; }

  blacklist_digest "sha256:dead"
  is_blacklisted "sha256:dead" || { echo "fail: blacklist miss"; exit 1; }
  is_blacklisted "sha256:live" && { echo "fail: unexpected blacklist hit"; exit 1; }

  FORCE_UPDATE=0
  force_update_enabled && { echo "fail: FORCE_UPDATE default"; exit 1; }
  FORCE_UPDATE=1
  force_update_enabled || { echo "fail: FORCE_UPDATE=1"; exit 1; }

  echo "pi-ota self-test ok"
}

main() {
  if [[ "${1:-}" == "--self-test" ]]; then
    run_self_test
    return 0
  fi

  cd "$APP_DIR"
  load_env
  ensure_state_dir

  if freeze_active && ! force_update_enabled; then
    log "freeze active (synced prod event); skipping OTA"
    exit 0
  fi
  if freeze_active && force_update_enabled; then
    log "WARNING: FORCE_UPDATE set while freeze active; proceeding"
  fi

  if ! ensure_free_space; then
    exit 0
  fi

  local be_ref fe_ref
  be_ref="${PI_BACKEND_IMAGE:-ghcr.io/osswald/order-platform:pi-backend-latest}"
  fe_ref="${PI_FRONTEND_IMAGE:-ghcr.io/osswald/order-platform:pi-frontend-latest}"

  local prev_be prev_fe
  prev_be="$(running_image_id pi-backend || true)"
  prev_fe="$(running_image_id pi-frontend || true)"

  log "pre-pulling images (live stack still serving)"
  "${COMPOSE[@]}" pull

  local new_be new_fe
  new_be="$(image_id "$be_ref")"
  new_fe="$(image_id "$fe_ref")"
  if [[ -z "$new_be" || -z "$new_fe" ]]; then
    log "could not resolve pulled image ids; aborting without apply"
    exit 1
  fi

  if [[ "$new_be" == "$prev_be" && "$new_fe" == "$prev_fe" ]]; then
    log "digests unchanged; nothing to apply"
    exit 0
  fi

  if ! force_update_enabled; then
    if is_blacklisted "$new_be" || is_blacklisted "$new_fe"; then
      log "pulled digest(s) blacklisted; skipping apply (await newer digest)"
      exit 0
    fi
  else
    log "WARNING: FORCE_UPDATE set; ignoring blacklist"
  fi

  local rc
  if [[ "$new_be" != "$prev_be" ]]; then
    set +e
    preapply_backend_health "$be_ref"
    rc=$?
    set -e
    if [[ "$rc" -eq 1 ]]; then
      blacklist_digest "$new_be"
      log "pre-apply backend health failed; keeping live stack"
      exit 0
    fi
    if [[ "$rc" -eq 2 ]]; then
      log "pre-apply backend infra failure; skipping apply this cycle"
      exit 0
    fi
  fi
  if [[ "$new_fe" != "$prev_fe" ]]; then
    set +e
    preapply_frontend_health "$fe_ref"
    rc=$?
    set -e
    if [[ "$rc" -eq 1 ]]; then
      blacklist_digest "$new_fe"
      log "pre-apply frontend health failed; keeping live stack"
      exit 0
    fi
    if [[ "$rc" -eq 2 ]]; then
      log "pre-apply frontend infra failure; skipping apply this cycle"
      exit 0
    fi
  fi

  log "short apply: compose up -d"
  compose_up

  if wait_http_ok "$HEALTH_URL" "$HEALTH_TIMEOUT_SEC"; then
    log "post-apply health ok"
    dangling_prune
    exit 0
  fi

  log "post-apply health failed; rolling back"
  blacklist_digest "$new_be"
  blacklist_digest "$new_fe"
  if [[ -n "$prev_be" && -n "$prev_fe" ]]; then
    apply_with_images "$prev_be" "$prev_fe" || log "rollback compose up failed"
    if wait_http_ok "$HEALTH_URL" "$HEALTH_TIMEOUT_SEC"; then
      log "rollback health ok"
    else
      log "rollback health still failing"
    fi
  else
    log "no previous image ids recorded; cannot rollback automatically"
  fi
  exit 1
}

main "$@"
