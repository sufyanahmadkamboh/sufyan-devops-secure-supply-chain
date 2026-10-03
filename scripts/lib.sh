#!/usr/bin/env bash
# Shared helpers. On the host only Docker, kind and Bash are needed; every other CLI runs in the
# pinned toolbox image (tools/toolbox), attached to the kind network.
# Strict mode for scripts only: `source scripts/lib.sh` in your own terminal must not close it on the first error.
[[ $- == *i* ]] || set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export MSYS_NO_PATHCONV=1   # Git Bash on Windows: keep /paths as they are
ROOT_NATIVE="$(cd "$ROOT" && { pwd -W 2>/dev/null || pwd; })"

CLUSTER="${CLUSTER:-supply-chain}"
TOOLBOX_IMAGE="${TOOLBOX_IMAGE:-ssc-toolbox:dev}"
KIND="${KIND:-kind}"
export STATE="$ROOT/.lab"   # kubeconfig and run state (git-ignored)

log() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
ok()  { printf '\033[1;32m ok\033[0m %s\n' "$*"; }
die() { printf '\033[1;31mERR\033[0m %s\n' "$*" >&2; exit 1; }

# Run a command in the toolbox, with the repository at /work and the cluster's internal kubeconfig.
tb() {
  docker run --rm -i --network kind \
    -v "$ROOT_NATIVE:/work" -w /work \
    -e KUBECONFIG=/work/.lab/kubeconfig \
    -e COSIGN_YES=true -e GITHUB_TOKEN -e GHCR_USER \
    "$TOOLBOX_IMAGE" "$@"
}
k() { tb kubectl "$@"; }

# Wait until a command succeeds; prints the seconds it took.
wait_for() {
  local timeout="$1"; shift
  local start; start=$(date +%s)
  until "$@" >/dev/null 2>&1; do
    (( $(date +%s) - start > timeout )) && return 1
    sleep 3
  done
  echo $(( $(date +%s) - start ))
}
