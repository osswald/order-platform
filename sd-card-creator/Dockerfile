# Linux builder for Vendiqo Pi SD images (SDM). Intended for docker compose on macOS.
FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    curl \
    xz-utils \
  && rm -rf /var/lib/apt/lists/*

# SDM and its Debian dependencies (systemd-container, qemu-user-static, …)
RUN curl -fsSL https://raw.githubusercontent.com/gitbls/sdm/master/install-sdm | bash

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

WORKDIR /workspace
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
