## Context

Production Pis run `docker-compose.prod.yml` with GHCR images (`:pi-*-latest` by default). Two systemd paths update them today:

- `vendiqo-pi.service`: `ExecStartPre=…pull` then `up -d` on every boot (`TimeoutStartSec=0` can wait forever on GHCR).
- `vendiqo-pi-update.timer`: every ~15 minutes runs the same `pull` + `up -d`.

There is no event-aware gate. Event lifecycle is `config → test → prod → archive`; the Pi syncs `test`/`prod` events in the config bundle. A bad `:latest` image has already taken venues down mid-service; operators needed power-cycles and once an SSH hotfix.

Constraints: single SQLite writer (no true zero-downtime backend), backend not published on the host (only nginx `:80`), venue networks are unreliable, SD cards are small, host update logic must not depend on a healthy API when deciding freeze if possible.

## Goals / Non-Goals

**Goals:**

- Do not apply container updates while any synced bundle event has status `prod`.
- Minimize (not eliminate) outage: free-space gate → pre-pull while serving → **required** pre-apply health of new image(s) → short recreate → post-apply verify → rollback + digest blacklist on failure.
- On boot: bring up **last-known-good** images immediately; run the same OTA path after a **5 minute** delay (`OnBootSec=5min`), still respecting freeze and blacklist.
- After successful apply, prune unused/dangling images so SD cards do not accumulate every historical `:latest`.
- Refuse to pull when free disk space is below `OTA_MIN_FREE_BYTES` (**2 GiB** default); on that failure, attempt dangling prune and re-check before giving up.
- Provide an emergency override so operators can force an update via SSH.

**Non-Goals:**

- True zero-downtime / blue-green with dual SQLite writers.
- Changing GHCR publish policy (candidate soak / promote-to-`latest` CI) — complementary follow-up.
- Cloud UI to manage freeze/blacklist (local files + logs are enough for MVP).
- Freezing on `test` events (updates during test are desirable).

## Decisions

### 1. Freeze signal: host-readable state dir, written by Pi backend

**Decision:** Bind-mount a host directory (e.g. `/opt/vendiqo/pi/ota-state`) into `pi-backend` (e.g. `/ota-state`). On each successful config-bundle apply (and on startup if bundle already present), the backend writes:

- `freeze` — present (or contains `1`) iff **any** event in the synced bundle has `status` normalizing to `prod`.
- Clear / write `0` when no synced event is `prod`.

The host OTA script reads this path directly (no HTTP to backend required for the freeze decision).

**Alternatives considered:**

- HTTP to `/health` or a new endpoint — backend has no host port in prod compose; would need `docker exec` or publishing a port.
- Reading SQLite from the named volume on the host — fragile schema coupling and locking.
- Cloud-pushed freeze flag — unnecessary when the Pi already has event status locally; adds offline failure modes.

### 2. Freeze semantics: block **apply**, allow no-op / skip entire OTA

**Decision:** When freeze is active (and override is unset), the OTA script exits successfully without `pull` or `up`. Do not pre-pull during freeze either (avoids filling the SD during the event for an apply that cannot run).

**Override:** `FORCE_UPDATE=1` in `/opt/vendiqo/pi/.env` (or a drop-in env file sourced by the script) bypasses freeze and blacklist for one recovery path. Document in `pi/README.md` / deploy docs. Free-space gate still applies unless a separate break-glass is documented (default: free-space still blocks even with `FORCE_UPDATE`, to avoid filling a dying SD; operators can lower the threshold in env if needed).

### 3. Shared OTA script for timer and delayed boot

**Decision:** Replace raw compose commands with `pi/deploy/pi-ota-update.sh` (name flexible) invoked by:

- `vendiqo-pi-update.service` (timer, ~15 min)
- Boot path: `vendiqo-pi.service` only runs `up -d` with **already present** images (remove `ExecStartPre=pull`). Update timer keeps **`OnBootSec=5min`** for the delayed first OTA after boot; do not reintroduce boot-blocking pull.

**Flow:**

```
1. If freeze && !FORCE_UPDATE → exit 0
2. Free-space check on Docker data filesystem (or /):
   if below OTA_MIN_FREE_BYTES (default 2 GiB):
     dangling prune (best-effort) → re-check;
     if still below → log, exit 0 (retry later); do not blacklist
3. Resolve desired image refs from compose/.env
4. docker compose pull (pre-pull; old containers still running)
5. Resolve new digests; if both match currently running → exit 0
6. If any new digest is blacklisted → skip apply, exit 0 (log)
7. Required pre-apply health of new image(s) in side containers (see decision 4);
   on failure → blacklist digest(s), do not stop running stack, no prune
8. Record previous image digests / compose project state for rollback
9. docker compose up -d (short outage)
10. Post-apply: poll http://127.0.0.1/health (via frontend) until OK or timeout
11. On failure → roll back to previous digests, blacklist failed digests, exit non-zero (**do not prune**)
12. On success → clear nothing from blacklist; **prune unused/dangling images** (see decision 9)
```

### 4. Health checks (pre-apply required)

**Decision:**

- **Pre-apply health is required** before stopping the live stack whenever a new digest would be applied.
- **Post-apply health is required** for success (existing `/health` via published `:80`).

**Pre-apply approach (safe w.r.t. SQLite):**

Pi backend `/health` does not touch the database. Run the newly pulled `pi-backend` image as an ephemeral container on `pi-net` **without** mounting `pi-data`, wait until its `/health` returns OK (or timeout). For `pi-frontend`, run the new nginx image ephemerally and verify it serves HTTP successfully (e.g. static root or a trivial request). Tear down side containers before apply.

Do **not** skip pre-apply. If the probe cannot be started (Docker error), treat as failure: do not apply, do not blacklist solely for infra errors (log and retry next timer) — blacklist only when the new image starts but fails health, or when health is definitively unhealthy.

Failed pre-apply health (image unhealthy) → blacklist digest(s), keep live stack. Failed post-apply → rollback + blacklist.

### 5. Free-space gate before pull (with prune retry)

**Decision:** Before `docker compose pull`, measure free space on the filesystem that holds Docker images (prefer Docker root dir from `docker info`, fallback `/var/lib/docker` or `/`). Default threshold: **`OTA_MIN_FREE_BYTES=2147483648` (2 GiB)**, overridable via env.

If below threshold:

1. Attempt the same conservative dangling prune as after success (decision 9) — live stack untouched.
2. Re-measure free space.
3. If now at/above threshold → continue with pull.
4. If still below → skip pull/apply, log clearly, exit 0 (no failure storm). Do not blacklist.

Rationale: free-space failures are often caused by accumulated dangling layers from earlier pulls; waiting for a successful apply to prune would deadlock (“can’t update because full; can’t free because can’t update”).

**Alternatives considered:** Percentage-only threshold — absolute bytes are simpler on fixed SD sizes. Skip prune on free-space fail and only retry next timer — slower recovery; rejected.

### 6. Blacklist by image digest (no expiry)

**Decision:** Persist failed digests under `ota-state/blacklist` (one digest per line, or JSON). Key by content digest (`sha256:…`) for backend and frontend separately. A newer `:latest` that resolves to a **different** digest is eligible again. Blacklist entries **MUST NOT expire by time** — only a newer digest, manual file clear, or `FORCE_UPDATE=1` clears the block for that digest.

### 7. Scope of “synced event is prod”

**Decision:** Freeze if **any** event in the current config bundle has status `prod` (after the same normalization the rest of the stack uses: lowercase; canonical value `prod`). Not limited to the waiter-selected event. `test`-only bundles do not freeze.

### 8. Rollback mechanism

**Decision:** Before apply, record the image IDs currently used by running containers. On post-apply failure, `docker compose up -d` with those digests (via temporary override or `docker tag` / `PI_*_IMAGE` digest pins for the rollback invocation only) so the previous known-good containers return. Do not leave the stack on the failed digest.

### 9. Image prune: after successful apply, or when free-space gate fails

**Decision:** Run a conservative Docker image prune (`docker image prune -f`, dangling only) in two cases:

1. After post-apply `/health` succeeds (reclaim superseded layers).
2. When the free-space gate fails, **before** giving up — then re-check space (decision 5).

Do **not** run `docker image prune -a` / filterless deletion of all unused tagged images in MVP unless filters guarantee running compose images are kept.

**Must not prune when:**

- OTA was skipped for freeze, blacklist skip, or unchanged digests (no disk emergency)
- Pre-apply health failed (live stack untouched; not a free-space path)
- Post-apply health failed (rollback just restored prior digests; those layers must remain)

Prune failures MUST be logged and MUST NOT reverse a successful apply; on the free-space path, prune failure simply leaves the gate failed.

**Alternatives considered:**

- Aggressive `prune -a` every run — frees more space but can delete the only rollback candidate if a later step needs it; rejected for MVP.
- Prune on a separate timer — simpler coupling, but then freeze windows would still GC; tying routine prune to successful apply keeps “we just proved the new stack works” as the safety boundary, with free-space-fail as the escape hatch.

## Risks / Trade-offs

- **[Risk] Freeze file stale if backend never syncs** → Mitigation: treat missing freeze file as “not frozen” only when no bundle exists; once a bundle with `prod` was seen, keep freeze until a later sync clears it. On unpaired Pi, no freeze (updates OK for setup).
- **[Risk] Rollback fails (image GC’d)** → Mitigation: never prune on health-failed apply/rollback; dangling-only prune keeps tagged/in-use images; free-space-fail prune is the same conservative mode.
- **[Risk] Short outage still drops in-flight orders** → Accepted; freeze ensures this only happens outside `prod`.
- **[Risk] Bad image blacklisted but `:latest` tag unchanged** → By design until CI publishes a new digest; log clearly so ops knows why updates are no-ops.
- **[Risk] `FORCE_UPDATE` during live event** → Document as break-glass only; script should log loudly.
- **[Risk] Pre-apply `/health` without DB misses migration failures** → Post-apply + rollback remains the safety net for migrate/runtime issues.
- **[Risk] Dangling-only prune leaves tagged unused images** → Accepted for MVP safety; free-space gate still blocks pull when the card is critically full.
- **[Risk] Free-space threshold too high/low** → Configurable via env; document default and how to override on field units.

## Migration Plan

1. Ship backend freeze writer + compose bind-mount (harmless if script not yet updated).
2. Ship `pi-ota-update.sh` + update systemd units; remove boot `pull`.
3. Refresh SD image / `install-vendiqo-pi.sh` for new devices; document one-shot upgrade commands for field Pis.
4. Rollback of the feature: restore previous unit files and remove bind-mount (freeze files can remain unused).

## Open Questions

- (none locked from review: boot delay **5 min**, `OTA_MIN_FREE_BYTES` **2 GiB**, blacklist **no time expiry**, prune also on free-space-fail + re-check.)
