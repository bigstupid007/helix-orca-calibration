FROM ubuntu@sha256:5ec03bb3441e8b0bf3b4f9cd4629a1ae763010dc3035bb8da3ae6cf026486401

LABEL org.opencontainers.image.title="HelixScreen beta.4 reproducible developer builder"
LABEL org.helixscreen.source.commit="13a77bec42616d5c6f4fa397f1d5e12682fa4376"

# Mirrors the pinned beta.4 Ubuntu build workflow's application-build
# dependencies. Tests, shell tooling, and release packaging are intentionally
# omitted: this image produces only build/bin/helix-screen for the mock harness.
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        ca-certificates \
        clang \
        cmake \
        git \
        libcairo2-dev \
        libbluetooth-dev \
        libfmt-dev \
        libjpeg-dev \
        libnl-3-dev \
        libnl-genl-3-dev \
        libpango1.0-dev \
        libpng-dev \
        libsdl2-dev \
        libssl-dev \
        libsystemd-dev \
        libusb-1.0-0-dev \
        make \
        npm \
        pkg-config \
        python3 \
        python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /source
