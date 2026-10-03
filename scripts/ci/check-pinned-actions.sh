#!/usr/bin/env bash
# Fails if any workflow uses a third-party action by tag or branch instead of a full commit SHA.
# Tags can be moved to malicious commits (this happened in 2025-2026: tj-actions/changed-files,
# actions-cool/issues-helper); a 40-character commit SHA cannot be changed.
set -euo pipefail
cd "$(dirname "$0")/../.."

bad=0
while IFS= read -r line; do
  file="${line%%:*}"
  ref="$(sed -E 's/.*uses:[[:space:]]*["'\'']?([^"'\''[:space:]#]+).*/\1/' <<<"$line")"
  case "$ref" in
    ./*|docker://*@sha256:*) continue ;;   # local workflows/actions, digest-pinned containers
  esac
  if [[ ! "$ref" =~ @[0-9a-f]{40}$ ]]; then
    echo "NOT PINNED: $file -> $ref"
    bad=1
  fi
done < <(grep -RHE '^[[:space:]-]*uses:' .github/workflows)

if (( bad )); then
  echo "Pin every action to a full commit SHA (keep the version as a comment: @<sha> # vX.Y.Z)." >&2
  exit 1
fi
echo "all actions are pinned to commit SHAs"
