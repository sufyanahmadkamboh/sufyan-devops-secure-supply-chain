# Runbook

## Protect the trust anchor (do this first in a real organisation)

Production trusts exactly one thing: signatures made by `.github/workflows/release.yaml` on `refs/heads/main`.
Whoever can change that file on main can release anything, so:

1. **Branch protection on `main`:** require pull requests, at least one approving review, and passing `ci`
   checks. Block force pushes. Include administrators.
2. **CODEOWNERS** (`.github/CODEOWNERS`): `.github/workflows/`, `policies/` and `platform/` need owner review.
3. **Actions settings:** allow only GitHub-owned and explicitly listed actions; require SHA pinning (the repo
   also enforces it with `scripts/ci/check-pinned-actions.sh`).
4. **Environments (optional):** put the `promote` job behind a protected environment for a manual approval.
5. Keep Dependabot enabled. It updates the pinned SHAs and digests weekly.

## Daily operation

| What | Where |
|---|---|
| Was anything blocked in prod? | Grafana "Software supply chain", top row; alert `UntrustedWorkloadBlocked` |
| What runs in prod, exactly? | `kubectl -n prod get pods -o jsonpath='{..image}'`: always `...@sha256:` |
| Which commit is that? | `cosign verify-attestation --type slsaprovenance1 --certificate-identity <release identity> --certificate-oidc-issuer https://token.actions.githubusercontent.com <image@digest> \| jq -r .payload \| base64 -d \| jq .predicate.buildDefinition.resolvedDependencies` |
| What's inside it? | the SBOM attestation (`--type cyclonedx`), or the `supply-chain-evidence` artifact of the release run |
| New CVEs in running images? | alert `RunningImageHasCriticalVulnerabilities`; `kubectl get vulnerabilityreports -A` |

## Alerts

| Alert | First steps |
|---|---|
| UntrustedWorkloadBlocked | `kubectl -n prod get events --field-selector reason=FailedCreate` and `reason=PolicyViolation`: which image, which rule? Then check who changed git (`git log deploy/`), who pushed to GHCR (package audit log), and whether a deploy key or token leaked. A one-off by a colleague deploying by hand is the most common cause. |
| RunningImageHasCriticalVulnerabilities | Is a fixed base image or dependency available? Then rebuild: a push to main releases a new signed digest. If no fix exists, record the accepted risk and set a review date. |
| AdmissionControllerDown | `kubectl -n kyverno get pods`. With `failurePolicy: Fail`, new pods cannot be created until Kyverno is back (running pods are unaffected). |

## Release a new version

Merge to `main`. The release workflow then:
1. builds and scans the image
2. signs it
3. runs the attack test against the new digest
4. commits it to `deploy/prod`

Argo CD deploys it within its refresh interval (about 3 minutes, or immediately with a hard refresh).

## Roll back

Revert the `deploy: storefront-api <digest>` commit in git. Argo CD deploys the previous, still-signed digest. Old
digests stay verifiable because their signatures and Rekor entries remain.

## Emergency: run an image that cannot be verified

Do not delete the policies. Create a reviewed, time-limited `PolicyException` for one namespace and one
workload, merged through git, so the exception is visible, reviewed and has an owner. Remove it after the
incident.

## Rotate / revoke

- There are **no signing keys** to rotate (keyless).
- To stop trusting a compromised build:
  1. change the identity in `policies/base/verify-images.yaml`, for example to a new workflow file name
  2. re-release
  3. images signed under the old identity are then refused at their next Pod creation

## Local lab

```bash
scripts/platform-up.sh          # kind + Kyverno + policies + Argo CD + Trivy Operator + Prometheus/Grafana
kubectl --kubeconfig .lab/kubeconfig ...   (or: source scripts/lib.sh; k get pods -A)
```

The full attack test (`scripts/e2e.sh`) runs in GitHub Actions. It needs a GitHub OIDC token for keyless
signing and write access to GHCR.
