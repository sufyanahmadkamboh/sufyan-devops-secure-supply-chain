#!/usr/bin/env bash
# Installs the CI tools from their official release downloads, each checked against a pinned SHA-256.
# Usage: scripts/ci/install-tools.sh cosign syft trivy kind actionlint
# (Downloading and verifying binaries ourselves keeps third-party GitHub Actions out of the pipeline.)
set -euo pipefail

BIN="${BIN_DIR:-$HOME/.local/bin}"
mkdir -p "$BIN"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

fetch() {  # url sha256 file
  curl -fsSL --retry 3 -o "$work/$3" "$1"
  echo "$2  $work/$3" | sha256sum -c - >/dev/null
}

for tool in "$@"; do
  case "$tool" in
    cosign)
      fetch https://github.com/sigstore/cosign/releases/download/v3.1.3/cosign-linux-amd64 \
        4629c757b7618056f8ddd7e2625ae9fdd94c0372a65049520bc7d9df9efc7f71 cosign
      install -m 0755 "$work/cosign" "$BIN/cosign" ;;
    syft)
      fetch https://github.com/anchore/syft/releases/download/v1.54.0/syft_1.54.0_linux_amd64.tar.gz \
        54a87372498168b2d033e876fd41fa4e8035b872699e525a57046e1f2f09c860 syft.tgz
      tar -xzf "$work/syft.tgz" -C "$work" syft && install -m 0755 "$work/syft" "$BIN/syft" ;;
    trivy)
      fetch https://github.com/aquasecurity/trivy/releases/download/v0.75.0/trivy_0.75.0_Linux-64bit.tar.gz \
        c6e65abddb348e25f10549df887045629cf28cc72453cd1c63acb717316b3f3f trivy.tgz
      tar -xzf "$work/trivy.tgz" -C "$work" trivy && install -m 0755 "$work/trivy" "$BIN/trivy" ;;
    kind)
      fetch https://github.com/kubernetes-sigs/kind/releases/download/v0.33.0/kind-linux-amd64 \
        aee6151561422756b764a4ae28e7f44cda5af5a9eead3cc9985112b1de8d8e0d kind
      install -m 0755 "$work/kind" "$BIN/kind" ;;
    actionlint)
      fetch https://github.com/rhysd/actionlint/releases/download/v1.7.12/actionlint_1.7.12_linux_amd64.tar.gz \
        8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8 actionlint.tgz
      tar -xzf "$work/actionlint.tgz" -C "$work" actionlint && install -m 0755 "$work/actionlint" "$BIN/actionlint" ;;
    *) echo "unknown tool: $tool" >&2; exit 2 ;;
  esac
  echo "installed $tool"
done
if [[ -n "${GITHUB_PATH:-}" ]]; then echo "$BIN" >> "$GITHUB_PATH"; fi
