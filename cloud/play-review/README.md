# Play review Pi (Google Play demo backend)

Always-on Pi stack for Google Play review at `https://play-review.demo.vendiqo.ch`.

## VPS setup (once)

1. Copy `cloud/play-review/.env.example` to `.env` on the VPS and fill in edge credentials from cloud admin (Play Review Demo appliance).
2. Set `PLAY_REVIEW_CLEANUP_SECRET` (shared with GitHub secret of the same name) for nightly purge.
3. Optionally set `PLAY_REVIEW_EVENT_ID` and `PLAY_REVIEW_CLOUD_TOKEN` so cleanup also purges cloud operational mirror/stock for that event.
4. Install the Caddy snippet from `caddy/play-review.caddy`:
   - Set `FRONTEND_CONTAINER` to the frontend container name after first `docker compose up` (project name `play-review`).
   - Copy into the host Caddy snippets dir (same as hosted Cloud-Pi; default `/caddy-snippets` on VPS).
   - Reload Caddy: `docker exec cloud-caddy-1 caddy reload --config /etc/caddy/Caddyfile`
5. Ensure `*.demo.vendiqo.ch` DNS points at the VPS.

## Manual deploy

From the repo root on the VPS (or via SSH):

```sh
./scripts/deploy-play-review.sh
```

This pulls latest Pi images, wipes the `pi-data` volume (clean demo event), restarts, runs sync pull, and requires public `GET /health` to return backend JSON (`status=ok`) with CORS for `https://appassets.androidplatform.net`.

## Nightly operational cleanup

Same purge semantics as event **test → prod** (orders and related rows; emulated receipts on Pi), without changing event status or wiping the volume:

```sh
./scripts/cleanup-play-review.sh
```

Scheduled via `.github/workflows/play-review-cleanup.yml` (~03:00 UTC daily).

## GitHub Actions

`.github/workflows/play-review-deploy.yml` runs after successful `pi-docker.yml` on `main` when `PLAY_REVIEW_DEPLOY_SSH_KEY` and host secrets are configured.

See [docs/play-store.md](../../docs/play-store.md) for the full operator checklist.
