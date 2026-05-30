# Vendiqo Pi SD card image (SDM on Linux)

Build a **generic** Raspberry Pi OS image with [sdm](https://github.com/gitbls/sdm). Run the build on a **Linux host** — on macOS, use an **Ubuntu VM in UTM** (Docker Desktop cannot run SDM’s systemd-nspawn customize step).

The image has **no** `EDGE_CLIENT_ID` or `EDGE_SECRET`. Pair each SD card on first boot (see [First boot](#first-boot)).

## Quick start (UTM + Ubuntu)

1. Install [UTM](https://mac.getutm.app/) and create an **Ubuntu 24.04 LTS** VM.
   - On Apple Silicon, prefer an **arm64** Ubuntu image (faster arm64 Pi image customization).
   - Allocate **≥ 32 GB** disk and **≥ 4 GB RAM**.
2. Clone this repo in the VM (or use a shared folder).
3. Configure the local Pi login password:

   ```bash
   cd sd-card-creator
   cp .env.example .env
   editor .env
   ```

   Set exactly one of `PI_PASSWORD` or `PI_PASSWORD_HASH`.

4. Build:

   ```bash
   ./build-on-ubuntu.sh
   ```

5. Flash `output/vendiqo-pi-*.img` or `output/vendiqo-pi-*.img.xz` with [Raspberry Pi Imager](https://www.raspberrypi.com/software/).

`build-on-ubuntu.sh` installs host packages and SDM (if needed), downloads the base image (see below), then runs `build-sdm-image.sh` with sudo.

## macOS without UTM

Use UTM Ubuntu or any other Linux machine with native SDM. Building inside Docker on Mac is **not supported** (SDM Phase 1 needs host systemd/nspawn).

## Network

The image installs a NetworkManager connection for the wired Ethernet port:

```text
address: 192.168.192.10/23
gateway: 192.168.192.1
dns:     192.168.192.1, 1.1.1.1
```

The profile uses `match-device=type:ethernet` so it works whether the kernel names the port `eth0`, `end0`, or similar. Source: [`pi/deploy/networkmanager-vendiqo-eth0.nmconnection`](../pi/deploy/networkmanager-vendiqo-eth0.nmconnection), applied via SDM `network` plugin.

## Build configuration

Set **`BASE_IMG_URL`** in [`.env`](.env) (copy from [`.env.example`](.env.example)). Default points at Raspberry Pi OS Lite arm64 Trixie; see [downloads.raspberrypi.com](https://downloads.raspberrypi.com/).

The same `.env` file configures Raspberry Pi OS first-boot prompts through SDM:

| Variable | Default | Role |
|----------|---------|------|
| `PI_LOCALE` | `en_GB.UTF-8` | System locale |
| `PI_KEYMAP` | `ch` | Swiss German keyboard layout |
| `PI_TIMEZONE` | `Europe/Zurich` | System timezone |
| `PI_WIFI_COUNTRY` | `CH` | WiFi regulatory country |
| `PI_USERNAME` | `vendiqo-user` | Local OS user |
| `PI_PASSWORD` | empty | Plaintext password, kept only in local `.env` |
| `PI_PASSWORD_HASH` | empty | Hashed password alternative to `PI_PASSWORD` |

Set exactly one of `PI_PASSWORD` or `PI_PASSWORD_HASH`; `.env` is gitignored.
Use `sudo sdm --info locale`, `sudo sdm --info keymap`, `sudo sdm --info timezone`, and `sudo sdm --info wifi` to list valid values.

## Output

Flashable files appear under **`output/`**:

- `vendiqo-pi-*.img`
- `vendiqo-pi-*.img.xz`

## Cache

- **`input/base.img`** — reused on the next run if it already exists. Delete it to force a fresh download.
- Large files under `input/` and `output/` are gitignored.

## What SDM installs

[`build-sdm-image.sh`](build-sdm-image.sh) uses SDM plugins (no custom phase script):

| Plugin | Role |
|--------|------|
| `user` | Create `PI_USERNAME` with the configured password |
| `L10n` | Apply locale, Swiss German keyboard, timezone, and WiFi country |
| `disables` | Disable `piwiz` so first boot does not ask for setup values |
| `apps` | `ca-certificates`, `curl`, `network-manager`, `xz-utils` |
| `docker-install` | Docker Engine per upstream install guide |
| `network` | Static wired Ethernet via `nmconn` from `pi/deploy/` |
| `copyfile` | `docker-compose.prod.yml`, systemd units under `/etc/systemd/system` |
| `system` | Enable `NetworkManager`, `docker`, `vendiqo-pi`, `vendiqo-pi-update.timer` |

Deploy assets live under [`pi/`](../pi/) (`deploy/`, `docker-compose.prod.yml`).

## First boot

After flashing:

1. Plug Ethernet into the Verleiher router
2. Boot the Pi
3. Open `http://192.168.192.10`
4. Enter the cloud pairing code (see [`pi/README.md`](../pi/README.md) — Cloud pairing)

Credentials are stored in `/data/edge.env` inside the persistent Docker volume.

## Advanced: manual build

If SDM and dependencies are already installed:

```bash
# optional: set BASE_IMG_URL in .env, then download via build-on-ubuntu.sh once,
# or place your own base image at input/base.img
# required: set PI_PASSWORD or PI_PASSWORD_HASH in sd-card-creator/.env

sudo sd-card-creator/build-sdm-image.sh \
  --base-img sd-card-creator/input/base.img \
  --output-dir sd-card-creator/output
```

Run from the **repository root** (paths above are relative to repo root).

## Troubleshooting

- **`Failed to open system bus` / nspawn errors** — You are not on a real Linux host with systemd (e.g. Docker on Mac). Use UTM Ubuntu and `./build-on-ubuntu.sh`.
- **Incomplete `vendiqo-pi-*.img` after a failed run** — Do not flash; delete the partial file and rebuild.
- **amd64 Ubuntu VM on Apple Silicon** — SDM uses `qemu-user-static` for arm64 images; the first build may be slower than on an arm64 VM.
- **No network on the Pi after boot** — The static profile only applies on the Verleiher router (`192.168.192.0/23`). Confirm Ethernet is plugged in and run `nmcli device status` / `ip -4 addr`. The connection matches the first wired port (`match-device=type:ethernet`), not a fixed interface name.
- **Older image with Tailscale** — If an earlier build installed Tailscale, `tailscaled` can interfere with local routing until removed: `sudo systemctl disable --now tailscaled && sudo apt-get remove -y tailscale`.

## Files in this directory

| File | Purpose |
|------|---------|
| `build-on-ubuntu.sh` | UTM/Linux entry point: deps, SDM, download, build |
| `build-sdm-image.sh` | Copy base `.img`, run `sdm --customize` with plugins, compress with `xz` |
| `lib/common.sh` | Load `.env`, download/cache `input/base.img` |
| `.env.example` | Default `BASE_IMG_URL` |
