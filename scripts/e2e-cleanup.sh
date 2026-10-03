#!/usr/bin/env bash
# Removes what the end-to-end test created outside the cluster: the temporary GitOps branch and the
# attacker image versions (tags e2e-*) in GHCR. Best effort: never fails the job.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 0
repo="${GITHUB_REPOSITORY:-sufyanahmadkamboh/sufyan-devops-secure-supply-chain}"
branch="$(cat .lab/e2e-branch 2>/dev/null || true)"
if [[ -n "$branch" && -n "${GITHUB_TOKEN:-}" ]]; then
  git push -q "https://x-access-token:${GITHUB_TOKEN}@github.com/${repo}.git" --delete "$branch" 2>/dev/null \
    && echo "deleted branch $branch"
fi
if [[ -n "${GITHUB_TOKEN:-}" ]]; then
  ids="$(curl -fsS -H "Authorization: Bearer ${GITHUB_TOKEN}" \
    "https://api.github.com/user/packages/container/storefront-api/versions?per_page=100" 2>/dev/null \
    | jq -r '.[] | select([.metadata.container.tags[]? | startswith("e2e-")] | any) | .id' 2>/dev/null)"
  for id in $ids; do
    curl -fsS -X DELETE -H "Authorization: Bearer ${GITHUB_TOKEN}" \
      "https://api.github.com/user/packages/container/storefront-api/versions/$id" >/dev/null 2>&1 \
      && echo "deleted attacker image version $id"
  done
fi
exit 0
