# Every CLI the project needs, pinned and checksum-verified. Used by the local lab and by CI,
# so both run exactly the same versions.
FROM debian:trixie-slim

ARG KUBECTL_VERSION=v1.37.1
ARG KUBECTL_SHA256=65691ff77eb6fa44c908b77a1082c9f092c3b9733b5cefabec0d1104890e21a8
ARG HELM_VERSION=v4.3.0
ARG HELM_SHA256=86584a54def73570558f66f5111cc53dfed56689637ae32c1201205d494f54fb
ARG COSIGN_VERSION=v3.1.3
ARG COSIGN_SHA256=4629c757b7618056f8ddd7e2625ae9fdd94c0372a65049520bc7d9df9efc7f71
ARG CRANE_VERSION=v0.22.1
ARG CRANE_SHA256=0ab7a1d6932a213aed964ce97666c3077fe691c8606413674a8b3e0b9ec4cda0
ARG KYVERNO_VERSION=v1.19.1
ARG KYVERNO_SHA256=b38228f367fc0fdc2b08f4c83ea50ac5f16c60ff8d62d76a66157c33c47b70ae

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# hadolint ignore=DL3008
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl jq git \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /tmp/tools
RUN curl -fsSLo kubectl "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl" \
 && echo "${KUBECTL_SHA256}  kubectl" | sha256sum -c - && install -m 0755 kubectl /usr/local/bin/ \
 && curl -fsSLo helm.tgz "https://get.helm.sh/helm-${HELM_VERSION}-linux-amd64.tar.gz" \
 && echo "${HELM_SHA256}  helm.tgz" | sha256sum -c - && tar -xzf helm.tgz && install -m 0755 linux-amd64/helm /usr/local/bin/ \
 && curl -fsSLo cosign "https://github.com/sigstore/cosign/releases/download/${COSIGN_VERSION}/cosign-linux-amd64" \
 && echo "${COSIGN_SHA256}  cosign" | sha256sum -c - && install -m 0755 cosign /usr/local/bin/ \
 && curl -fsSLo crane.tgz "https://github.com/google/go-containerregistry/releases/download/${CRANE_VERSION}/go-containerregistry_Linux_x86_64.tar.gz" \
 && echo "${CRANE_SHA256}  crane.tgz" | sha256sum -c - && tar -xzf crane.tgz crane && install -m 0755 crane /usr/local/bin/ \
 && curl -fsSLo kyverno.tgz "https://github.com/kyverno/kyverno/releases/download/${KYVERNO_VERSION}/kyverno-cli_${KYVERNO_VERSION}_linux_x86_64.tar.gz" \
 && echo "${KYVERNO_SHA256}  kyverno.tgz" | sha256sum -c - && tar -xzf kyverno.tgz kyverno && install -m 0755 kyverno /usr/local/bin/ \
 && cd / && rm -rf /tmp/tools

WORKDIR /work
CMD ["bash"]
