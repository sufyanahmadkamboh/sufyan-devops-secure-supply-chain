#!/usr/bin/env bash
# Writes a SLSA v1 provenance predicate for an image built in GitHub Actions, from the facts the
# runner provides (repository, workflow, commit, run). It is signed by `cosign attest`, so the claims
# are bound to the release workflow's identity: nobody else can produce a valid one.
#   scripts/ci/provenance.sh <image@digest> > provenance.json
set -euo pipefail

image="${1:?usage: provenance.sh <image@digest>}"   # the subject is added by cosign attest
: "$image"
: "${GITHUB_SERVER_URL:?run inside GitHub Actions}" "${GITHUB_REPOSITORY:?}" "${GITHUB_SHA:?}" "${GITHUB_REF:?}" \
  "${GITHUB_WORKFLOW_REF:?}" "${GITHUB_RUN_ID:?}" "${GITHUB_RUN_ATTEMPT:?}" "${RUNNER_ENVIRONMENT:=github-hosted}"

repo_url="$GITHUB_SERVER_URL/$GITHUB_REPOSITORY"
workflow_path="${GITHUB_WORKFLOW_REF#"$GITHUB_REPOSITORY"/}"
workflow_path="${workflow_path%@*}"

jq -n \
  --arg repo "$repo_url" \
  --arg ref "$GITHUB_REF" \
  --arg path "$workflow_path" \
  --arg sha "$GITHUB_SHA" \
  --arg builder "$repo_url/$workflow_path@$GITHUB_REF" \
  --arg run "$repo_url/actions/runs/$GITHUB_RUN_ID/attempts/$GITHUB_RUN_ATTEMPT" \
  --arg env "$RUNNER_ENVIRONMENT" \
  --arg started "${BUILD_STARTED_ON:-$(date -u +%FT%TZ)}" \
  --arg finished "$(date -u +%FT%TZ)" \
  '{
    buildDefinition: {
      buildType: "https://github.com/sufyanahmadkamboh/sufyan-devops-secure-supply-chain/buildtypes/docker-build/v1",
      externalParameters: {
        workflow: {repository: $repo, ref: $ref, path: $path}
      },
      internalParameters: {github: {runner_environment: $env}},
      resolvedDependencies: [
        {uri: ("git+" + $repo + "@" + $ref), digest: {gitCommit: $sha}}
      ]
    },
    runDetails: {
      builder: {id: $builder},
      metadata: {invocationId: $run, startedOn: $started, finishedOn: $finished}
    }
  }'
