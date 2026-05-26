# Vendiqo Raspberry Pi image build

This directory contains the first SDM scaffold for producing a generic, headless Raspberry Pi image.

The image is generic: it does **not** contain `EDGE_CLIENT_ID` or `EDGE_SECRET`. On first boot, connect a browser to:

```text
http://192.168.192.10
```

Then enter the pairing code generated from the cloud server appliance.

## Network

The image installs a NetworkManager connection for:

```text
eth0:    192.168.192.10/23
gateway: 192.168.192.1
dns:     192.168.192.1, 1.1.1.1
```

## Build

1. Install SDM on a Linux builder:

   ```bash
   curl -L https://raw.githubusercontent.com/gitbls/sdm/master/install-sdm | bash
   ```

2. Download and uncompress a Raspberry Pi OS Lite arm64 image from Raspberry Pi downloads.

3. Build the Vendiqo image:

   ```bash
   sudo pi/image/build-sdm-image.sh \
     --base-img /path/to/raspios-lite-arm64.img \
     --output-dir /tmp/vendiqo-pi-image
   ```

The script copies the base image, runs `sdm --customize`, and writes both:

```text
vendiqo-pi-*.img
vendiqo-pi-*.img.xz
```

## What SDM installs

- Docker Engine from Raspberry Pi OS/Debian packages
- Docker Compose plugin
- production Pi compose file
- static `eth0` NetworkManager profile
- `vendiqo-pi.service`
- `vendiqo-pi-update.timer`

## First boot

After flashing:

1. plug Ethernet into the Verleiher router
2. boot the Pi
3. open `http://192.168.192.10`
4. enter the cloud pairing code

The Pi stores edge credentials in `/data/edge.env` inside the persistent Docker volume.
