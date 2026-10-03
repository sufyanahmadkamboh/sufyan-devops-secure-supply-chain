#!/usr/bin/env bash
# Prints the state needed to debug a failed end-to-end run.
# shellcheck source=lib.sh
source "$(dirname "$0")/lib.sh"
k get pods -A -o wide || true
k -n prod get events --sort-by=.lastTimestamp | tail -n 30 || true
k -n argocd get application storefront-api -o yaml | tail -n 60 || true
k get vpol,ivpol || true
k -n kyverno logs deploy/kyverno-admission-controller --tail=80 2>&1 | grep -E 'ERR|WRN' | tail -n 40 || true
