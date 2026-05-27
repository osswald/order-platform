# Vendiqo Pi SD card image (Docker + SDM)

Build a **generic** Raspberry Pi OS image with [sdm](https://github.com/gitbls/sdm). On **macOS** (or any host without native SDM), use Docker here; on Linux you can run the same scripts on the host.

The image has **no** `EDGE_CLIENT_ID` or `EDGE_SECRET`. Pair each SD card on first boot (see [First boot](#first-boot)).

## Network

The image installs a NetworkManager connection for:

```text
eth0:    192.168.192.10/23
gateway: 192.168.192.1
dns:     192.168.192.1, 1.1.1.1
```

## Prerequisites (Docker)

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Mac or Windows) or Docker Engine (Linux)
- Several GB free disk space (download + expanded `.img` + Vendiqo output)

## Base image URL

Compose loads **`BASE_IMG_URL`** from **[`.env.example`](.env.example)**. To use another Raspberry Pi OS Lite arm64 release, edit that URL (see [downloads.raspberrypi.com](https://downloads.raspberrypi.com/)).

## Build (Docker)

```bash
cd sd-card-creator
docker compose build
docker compose up
```

Use foreground `docker compose up` so you see logs until the run finishes. The first run **downloads** the base image (can take a while).

## Output

Flashable files appear under **`sd-card-creator/output/`**:

- `vendiqo-pi-*.img`
- `vendiqo-pi-*.img.xz`

Flash with [Raspberry Pi Imager](https://www.raspberrypi.com/software/) or another imager.

## Cache

- **`input/base.img`** — reused on the next run if it already exists (skips download). Delete it to force a fresh download.
- **`input/`** may also hold a transient `base.img.xz` during download; large files are gitignored.

## What SDM installs

SDM customizes the base image using scripts in this directory and assets from [`pi/`](../pi/) (`deploy/`, `docker-compose.prod.yml`):

- Docker Engine and Docker Compose plugin
- production Pi compose file under `/opt/vendiqo/pi`
- static `eth0` NetworkManager profile
- `vendiqo-pi.service` and `vendiqo-pi-update.timer`

## First boot

After flashing:

1. Plug Ethernet into the Verleiher router
2. Boot the Pi
3. Open `http://192.168.192.10`
4. Enter the cloud pairing code (see [`pi/README.md`](../pi/README.md) — Cloud pairing)

Credentials are stored in `/data/edge.env` inside the persistent Docker volume.

## Native Linux (no Docker)

1. Install SDM:

   ```bash
   curl -L https://raw.githubusercontent.com/gitbls/sdm/master/install-sdm | bash
   ```

2. Download and uncompress Raspberry Pi OS Lite arm64 (or set `BASE_IMG_URL` and use the Docker download step once).

3. From the repo root:

   ```bash
   sudo sd-card-creator/build-sdm-image.sh \
     --base-img /path/to/raspios-lite-arm64.img \
     --output-dir /path/to/out
   ```

## Security / caveats

- Compose uses **`privileged: true`** and mounts **`/dev:/dev`** for loop devices and SDM. Only run on a trusted machine.
- **Docker Desktop on Mac** runs Linux in a VM; if `sdm --customize` fails on loop devices, try native Linux or a Linux VM.

## Files in this directory

| File | Purpose |
|------|---------|
| `build-sdm-image.sh` | Copy base `.img`, run `sdm --customize`, compress with `xz` |
| `sdm-customphase-vendiqo.sh` | SDM customization phases (invoked by SDM) |
| `entrypoint.sh` | Docker: download base image, then run `build-sdm-image.sh` |
