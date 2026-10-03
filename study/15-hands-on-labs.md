# 15. Hands-on labs

Start the lab once with `scripts/platform-up.sh`. All commands run from the repository root, in bash (Git Bash on Windows). Load the helpers in every new terminal:

```bash
source scripts/lib.sh     # tb = run a command in the toolbox, k = kubectl in the toolbox
ID=https://github.com/sufyanahmadkamboh/sufyan-devops-secure-supply-chain/.github/workflows/release.yaml@refs/heads/main
ISSUER=https://token.actions.githubusercontent.com
DIGEST="$(grep -oE 'sha256:[a-f0-9]{64}' deploy/prod/kustomization.yaml)"
IMG="ghcr.io/sufyanahmadkamboh/storefront-api@$DIGEST"
```

If `DIGEST` is still the all-zero placeholder, no release has been promoted yet: skip the parts marked **(needs a release)**, or run the release workflow in your fork first.

Compare what you observe with [`docs/test-results.md`](../docs/test-results.md).

## Lab 1: Look around

1. `k get pods -A`: find Kyverno, Argo CD, Trivy Operator, Prometheus and Grafana. Which namespace holds each?
2. `k get ivpol,vpol`: there are six policies. Why six, when `policies/base/` has three?
3. `k get ns prod sandbox --show-labels`: which label turns on Deny, which one Audit? Which label is Kubernetes' own Pod Security?
4. `k -n argocd get application storefront-api`: what are its sync and health status? If the digest is the placeholder, why is it unhealthy?
5. Open `docs/architecture.md` and find the "Trust boundaries" table. Which two attackers win?

## Lab 2: Verify the image like the cluster does (needs a release)

```bash
tb cosign verify --certificate-identity "$ID" --certificate-oidc-issuer "$ISSUER" "$IMG" | tb jq '.[0].optional'
for t in slsaprovenance1 vuln cyclonedx; do
  tb cosign verify-attestation --type "$t" --certificate-identity "$ID" --certificate-oidc-issuer "$ISSUER" "$IMG" >/dev/null && echo "ok $t"
done
```

1. In the `optional` block, find the commit SHA. Open that commit on GitHub.
2. Decode the provenance (chapter 7) and click the run URL in `runDetails.metadata.invocationId`. Is it the run that built this digest?
3. Change `release.yaml` to `ci.yaml` in `$ID` and verify again. What error do you get, and why is that the whole point?
4. `tb crane manifest "$IMG" | tb jq '.layers | length'`: how many layers does a distroless Go image have?

## Lab 3: Be the attacker at the door

1. Apply the foreign-image pod from chapter 8 (`try-foreign`). Read the denial message: which policy refused it?
2. (needs a release) Find the release tag with `tb crane ls ghcr.io/sufyanahmadkamboh/storefront-api | grep '^sha-'` and put `ghcr.io/sufyanahmadkamboh/storefront-api:sha-...` (a tag, not a digest) in that manifest. Bare Pods may use tags, so it is verified and admitted. Now `k -n prod get pod try-foreign -o jsonpath='{.spec.containers[0].image}'`: what did `mutateDigest` add? Delete the pod.
3. Same manifest with the trusted image, but add `privileged: true` and set `allowPrivilegeEscalation: true`. Who refuses it first: PSA or Kyverno? (Hint: read the start of the error message.)
4. Remove `seccompProfile` from the safe manifest. What changes?
5. `k -n prod get events --field-selector reason=PolicyViolation`: are your attempts recorded?

## Lab 4: Audit mode in the sandbox

```bash
k -n sandbox run unsafe --image=docker.io/library/busybox:1.37 --restart=Never -- sleep 3600
k -n sandbox get policyreports -o wide
k -n sandbox get policyreports -o json | tb jq -r '.items[].results[]? | select(.result=="fail") | "\(.policy): \(.message)"'
```

1. The pod runs. Which policies does the report say it would violate in prod?
2. Why is an audit namespace the safe way to introduce a new policy in a real company?
3. Delete the pod: `k -n sandbox delete pod unsafe`.

## Lab 5: Watch the scanner and the alert

```bash
k -n sandbox run legacy-nginx --image=docker.io/library/nginx:1.21.0 --restart=Never
# wait a few minutes, then:
k -n sandbox get vulnerabilityreports
k -n sandbox get vulnerabilityreports -o json | tb jq '.items[] | {image: .report.artifact.repository, summary: .report.summary}'
k -n monitoring exec deploy/prometheus -- wget -qO- 'http://localhost:9090/api/v1/alerts' | tb jq '.data.alerts[] | {alert: .labels.alertname, state}'
```

1. How long until the VulnerabilityReport appears? How long until `RunningImageHasCriticalVulnerabilities` is `pending`, then `firing`? Why the gap (`for: 5m`)?
2. Open Grafana (chapter 11) and find the image in "Vulnerabilities in running images".
3. Delete the pod. How long until the alert resolves?

## Lab 6: Break a policy, let the tests catch it

```bash
tb kyverno test policies/tests                       # all pass
# remove the ':' and '@' from the allowed-images prefix check:
sed -i 's|storefront-api:")|storefront-api")|; s|storefront-api@"))|storefront-api"))|' policies/base/allowed-images.yaml
tb kyverno test policies/tests                       # which test fails now?
git checkout -- policies/base/allowed-images.yaml    # undo
```

1. Which test resource is now wrongly accepted? Why is that a real attack (chapter 8)?
2. Write a new test resource: a Deployment using `ghcr.io/sufyanahmadkamboh/storefront-api@sha256:` with a 63-character digest. Add it to `kyverno-test.yaml` as `fail`. Does it pass?

## Lab 7: Break an alert, let promtool catch it

```bash
run_promtool() { docker run --rm -v "$ROOT_NATIVE:/w" -w /w/tests/prometheus --entrypoint promtool prom/prometheus:v3.15.0 test rules rules.test.yaml; }
run_promtool
sed -i 's|resource_namespace="prod"}\[10m\]|}[10m]|' platform/monitoring/rules.yaml   # count every namespace
run_promtool                                                                        # what fails?
git checkout -- platform/monitoring/rules.yaml
```

1. Which test case fails, and what would that mistake have meant at 3 a.m.?
2. Add a test that proves `UntrustedWorkloadBlocked` resolves 15 minutes after the last refusal.

## Lab 8: Pipeline hygiene

Create a throwaway workflow and let the checks find what is wrong:

```bash
cat > .github/workflows/lab-bad.yaml <<'EOF'
name: lab-bad
on: pull_request_target
permissions: write-all
jobs:
  greet:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - run: echo "Hello ${{ github.event.pull_request.title }}"
EOF
scripts/ci/check-pinned-actions.sh
pip install --require-hashes -r tools/zizmor-requirements.txt && zizmor .github/workflows/lab-bad.yaml
rm .github/workflows/lab-bad.yaml
```

1. List every problem the tools report. Map each to an attack from chapter 2.
2. Rewrite the file so it passes: pinned SHA, `permissions: {}` plus job-level `contents: read`, `persist-credentials: false`, the title passed through an `env:` variable instead of `${{ }}` inside `run:`.

## Lab 9: Follow a full release (needs a fork)

1. Fork the repository, enable Actions and GHCR, and update the repository name in the identity strings of `policies/base/verify-images.yaml` and the `IMAGE` value (a good exercise in where identities live: `grep -rn sufyanahmadkamboh .github policies deploy scripts platform`).
2. Push a small change to `app/main.go` on `main`.
3. Watch `release.yaml`: build, e2e, promote. Open the e2e step summary: every scenario and its result.
4. Download the `supply-chain-evidence` artifact and look at `provenance.json`.
5. Check that the promote commit changed only `deploy/prod/kustomization.yaml`.

## Clean up

```bash
kind delete cluster --name supply-chain
rm -rf .lab
```
