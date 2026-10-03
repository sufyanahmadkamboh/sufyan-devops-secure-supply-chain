# 13. The end-to-end attack test

## What is it?

[`scripts/e2e.sh`](../scripts/e2e.sh) builds the whole platform on a throwaway kind cluster inside GitHub Actions, deploys the freshly signed release through GitOps, and then **attacks it**: the way real attackers would, with real images in the real registry and real Sigstore signatures. Every scenario must end the expected way (blocked, or admitted for the control case), otherwise the release stops before promotion.

It runs as the reusable workflow [`.github/workflows/e2e.yaml`](../.github/workflows/e2e.yaml), called by `release.yaml` with the new digest.

## Why it exists

Policies that "look right" are not evidence. A typo in an identity, an attestation type that Kyverno cannot find, or a signature format it does not read would make every check silently fail open or closed. The only proof is to try the attacks against a real cluster with the real policies, on every release.

The results file (`reports/e2e-results.md`) and the measured times are recorded as evidence; see [docs/test-results.md](../docs/test-results.md) for the published results. This guide does not repeat any numbers.

## How it works: the six sections

| # | Section | What happens | Expected |
|---|---|---|---|
| 1 | Platform | temporary GitOps branch with the new digest; `platform-up.sh` with `ARGO_REVISION` = that branch | everything installed |
| 2 | Legitimate release | Argo CD syncs the signed digest | 2/2 pods run the verified digest; the service answers `/version` |
| 3 | Attacks at admission | see the table below | each attack blocked, control admitted |
| 4 | Attack through GitOps | commit the tampered digest to the branch | Argo CD applies it, Kyverno refuses the pods, old pods keep serving; revert syncs again |
| 5 | Sandbox | unsigned image and `nginx:1.21.0` in the audit namespace | allowed, listed in PolicyReports; Trivy Operator finds CRITICAL CVEs; the alert fires |
| 6 | Monitoring | read Prometheus alerts | `UntrustedWorkloadBlocked` firing, `AdmissionControllerDown` not firing |

### Section 3 in detail

| Scenario | How it is built | Which check stops it |
|---|---|---|
| foreign registry | `docker.io/library/nginx:1.29` | `allowed-images` |
| unsigned image in **our** repository | `crane copy busybox` into `storefront-api` (simulates a stolen registry token) | no signature |
| tampered image | `crane append` a "backdoor" layer onto the trusted image: new digest, same name | no signature for that digest |
| **imposter** | the tampered image, **really signed** by `e2e.yaml`, with forged provenance (builder and path edited to say `release.yaml`) and a fake "clean" scan | wrong certificate identity |
| privileged trusted image | the real signed image, `privileged: true` | `restricted-pods` (and PSA) |
| control | the real signed image, safe spec | must be **admitted** |

Why the imposter is the important one: it proves the identity check, not just "is there a signature". The script first confirms the signature is real and names `e2e.yaml`:

```bash
  subject="$(cosign verify --certificate-identity-regexp '.*' --certificate-oidc-issuer https://token.actions.githubusercontent.com "$TAMPERED" 2>/dev/null \
    | jq -r '.[0].optional.Subject')"
  if [[ "$subject" == *"/.github/workflows/e2e.yaml@"* ]]; then
    pass "imposter image carries a VALID Sigstore signature, identity: $subject"
```

(Here `--certificate-identity-regexp '.*'` is used on purpose, only to *read* the identity. Never use it to *trust* one.)

Then it expects the cluster to refuse it:

```bash
  expect_denied "tampered image signed by an imposter workflow with forged provenance" attack-imposter "$TAMPERED"
  expect_denied "trusted image started as a privileged container" attack-privileged "$TRUSTED" true
```

That is why `e2e.yaml` is a separate file (architecture decision 13): its jobs get a *different* certificate identity, which makes the imposter scenario possible without any trick.

### Every attack pod has a safe spec

`try_deploy` builds a pod that satisfies PSA `restricted` (non-root, seccomp, dropped capabilities, limits). Only the image (or `privileged`) changes. A refusal therefore really comes from the supply-chain rule being tested, not from an unrelated pod-security setting.

### Cleanup

[`scripts/e2e-cleanup.sh`](../scripts/e2e-cleanup.sh) runs with `if: always()`: it deletes the temporary branch and the attacker image versions (tags `e2e-*`) from GHCR. On failure, [`scripts/diagnostics.sh`](../scripts/diagnostics.sh) prints pods, prod events, the Argo CD Application, the policies and Kyverno errors.

## Try it

The full test needs a GitHub OIDC token, so it runs in Actions:

```bash
# in your fork, Actions tab -> "e2e" -> Run workflow, with the digest from deploy/prod/kustomization.yaml
# or locally, read it section by section:
grep -n "^s[1-6]()\|expect_denied\|pass \"" scripts/e2e.sh
```

Locally, the parts that need no signing can be replayed after `scripts/platform-up.sh`: the foreign-registry pod (chapter 8), the privileged pod (chapter 9), the sandbox scan (chapter 5).

`E2E_FROM=4 scripts/e2e.sh` resumes from section 4 when debugging a run.

## Common mistakes

- Testing only "the good image works". Without attack cases, a policy that admits everything also passes.
- Attack pods with an unsafe spec: they are refused by PSA, and the test looks green for the wrong reason.
- An imposter "signature" that silently failed to be created: then "blocked" proves nothing. The script asserts the signature exists first.
- Leaving attacker images and branches behind.

## Check yourself

1. Why does the script verify the imposter's signature before expecting a refusal?
2. Why must the control case be admitted?
3. What would break if the e2e test lived as a job inside `release.yaml` instead of in `e2e.yaml`?

### Answers

<details><summary>Answers</summary>

1. If signing had silently failed, the image would be refused simply for being unsigned, and the test would not prove that a *validly signed image from the wrong workflow* is refused.
2. Otherwise a policy that refuses everything would pass all attack cases. The control proves the defences are precise, not just closed.
3. Its signatures would carry the `release.yaml@refs/heads/main` identity, the trusted one. The test could no longer simulate a different workflow, and worse, it would be producing *trusted* signatures for a tampered image in the real registry.

</details>
