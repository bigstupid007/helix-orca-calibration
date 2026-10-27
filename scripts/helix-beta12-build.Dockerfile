FROM ubuntu@sha256:5ec03bb3441e8b0bf3b4f9cd4629a1ae763010dc3035bb8da3ae6cf026486401

LABEL org.opencontainers.image.title="HelixScreen beta.12 reproducible developer builder"
LABEL org.helixscreen.source.commit="00a9fe6030c37d56748b2122b41fd36de1fdf831"

# Mirrors beta.12's Ubuntu 22.04 application-build dependencies.
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        ca-certificates clang git libcairo2-dev libbluetooth-dev libfmt-dev \
        libjpeg-dev libnl-3-dev libnl-genl-3-dev libpango1.0-dev libpng-dev \
        libsdl2-dev libssl-dev libsystemd-dev libusb-1.0-0-dev libxml2-utils \
        make npm pkg-config python3 python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /source
