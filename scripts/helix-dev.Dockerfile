FROM ubuntu@sha256:5ec03bb3441e8b0bf3b4f9cd4629a1ae763010dc3035bb8da3ae6cf026486401

LABEL org.opencontainers.image.title="Helix-Orca native beta.4 test runtime"
LABEL org.helixscreen.source.commit="13a77bec42616d5c6f4fa397f1d5e12682fa4376"

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        ca-certificates \
        libasound2 \
        libfmt8 \
        libgles2 \
        libsdl2-2.0-0 \
        libssl3 \
        libsystemd0 \
        libusb-1.0-0 \
        zlib1g \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /helix
