#!/usr/bin/env bash
# Install Tailscale client and enable tailscaled (used by SDM runscript and manual deploy).
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

if command -v tailscale >/dev/null 2>&1; then
  echo "tailscale already installed"
else
  if ! command -v curl >/dev/null 2>&1; then
    echo "curl is required to install Tailscale" >&2
    exit 1
  fi
  curl -fsSL https://tailscale.com/install.sh | sh
fi

systemctl enable tailscaled.service

echo "Tailscale installed. Join the tailnet with: sudo tailscale up"
