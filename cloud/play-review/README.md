# Play review Pi (Google Play demo backend)

Always-on Pi stack for Google Play review at `https://play-review.demo.vendiqo.ch`.

## VPS setup (once)

1. Copy `cloud/play-review/.env.example` to `.env` on the VPS and fill in edge credentials from cloud admin (Play Review Demo appliance).
2. Install the Caddy snippet from `caddy/play-review.caddy`:
   - Set `FRONTEND_CONTAINER` to the frontend container name after first `docker compose up` (project name `play-review`).
   - Copy into the host Caddy snippets dir (same as hosted Cloud-Pi; default `/caddy-snippets` on VPS).
   - Reload Caddy: `docker exec cloud-caddy-1 caddy reload --config /etc/caddy/Caddyfile`
3. Ensure `*.demo.vendiqo.ch` DNS points at the VPS.

## Manual deploy

From the repo root on the VPS (or via SSH):

```sh
./scripts/deploy-play-review.sh
```

This pulls latest Pi images, wipes the `pi-data` volume (clean demo event), restarts, runs sync pull, and checks `/health`.

## GitHub Actions

`.github/workflows/play-review-deploy.yml` runs after successful `pi-docker.yml` on `main` when `PLAY_REVIEW_DEPLOY_SSH_KEY` and host secrets are configured.

See [docs/play-store.md](../../docs/play-store.md) for the full operator checklist.
