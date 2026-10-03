# 14. How everything fits together

This chapter follows **one legitimate release** and then **four attackers** through every tool, so you can see each protection in its place. Nothing here is new; it connects chapters 1 to 13.

## The layers, from code to running pod

| Layer | Tool / file | Question it answers |
|---|---|---|
| Pipeline hygiene | zizmor, actionlint, `check-pinned-actions.sh`, CODEOWNERS, Dependabot | Can someone hijack the pipeline itself? |
| Image content | distroless base pinned by digest, Go unit tests in the build | Is there little to attack, and does it work? |
| Known holes | Trivy gate | Does it contain fixable CRITICAL/HIGH CVEs? |
| Ingredients | Syft SBOM | What exactly is inside? |
| Identity | cosign keyless, Fulcio, Rekor | Who built it? (release.yaml on main) |
| Evidence | provenance, scan and SBOM attestations | From which code, how, and was it clean? |
| Self-check | `cosign verify` in release.yaml | Is what we published verifiable? |
| Proof | `e2e.yaml` attack test | Do the defences really work, on this release? |
| Delivery | promote job, Argo CD | Is the deployed digest exactly the tested one? |
| The door | Kyverno: `verify-release-images`, `allowed-images`, `restricted-pods`; PSA restricted | Is this pod allowed to start? |
| After delivery | Trivy Operator, Prometheus, Grafana | Has anything been refused? Did a running image become vulnerable? |

## One legitimate release

1. A developer opens a pull request. `ci.yaml` runs zizmor, actionlint, the pinned-actions check, Go tests, ShellCheck, hadolint, `kyverno test`, Kustomize rendering, promtool tests and yamllint. CODEOWNERS requires review of workflow and policy changes.
2. The merge to `main` starts `release.yaml`. The `build` job (with `id-token: write` only there) builds `storefront-api`, the Trivy gate passes, the image is pushed and its digest read back.
3. Syft writes the SBOM, Trivy writes the scan report, `provenance.sh` writes the SLSA provenance. cosign signs the digest and attaches three attestations; Fulcio issues a certificate for `release.yaml@refs/heads/main`; Rekor logs everything.
4. The job verifies its own output with the cluster's identity rule and uploads the `supply-chain-evidence` artifact.
5. `e2e.yaml` runs the six sections of chapter 13 against this digest. All attacks blocked, control admitted.
6. `promote` commits the digest to `deploy/prod/kustomization.yaml`.
7. Argo CD syncs. Kyverno already checks the Deployment update (same image rules) and admits it. The Deployment gets a new ReplicaSet; it asks for a pod.
8. PSA checks the pod spec (restricted). Kyverno runs `allowed-images`, `restricted-pods` and `verify-release-images`: signature by the right identity, provenance says this repository and `main`, signed scan has no CRITICAL/HIGH, signed SBOM exists. The image is rewritten to the verified digest.
9. The pod starts. Only when it is ready is an old pod removed (`maxUnavailable: 0`).
10. Trivy Operator scans the running image and keeps doing so. Grafana shows signature checks passing and nothing blocked.

## Four attackers

### Attacker 1: has a registry token
They push `storefront-api:latest` with a backdoor, or overwrite a tag.
- Production never uses tags: `allowed-images` requires a digest in workload specs, and git holds the digest.
- Even if they get a pod spec pointing to their digest, `verify-release-images` finds no signature from the release identity. **Refused.**
- Covered by e2e section 3 (unsigned, tampered).

### Attacker 2: can push to the deploy folder in git
They change the prod digest to their image.
- Argo CD syncs it: GitOps is not a security boundary.
- Kyverno refuses the new pods; old pods keep serving; `UntrustedWorkloadBlocked` fires. Rollback is `git revert`.
- Covered by e2e section 4.

### Attacker 3: injects a workflow into the repository
Their workflow gets an OIDC token, signs their image, attests forged provenance that *says* `release.yaml` and a fake clean scan.
- Fulcio certifies who they really are: their workflow file, not `release.yaml`. The policy compares the certificate identity, not the text inside the provenance. **Refused.**
- Pipeline hygiene (zizmor, pinned actions, CODEOWNERS, branch protection) makes the injection itself harder.
- Covered by e2e section 3 (imposter).

### Attacker 4: uses the genuine image, dangerously
They start the real, signed image as a privileged container with the host file system mounted.
- `restricted-pods` and PSA refuse it. **Refused.**
- Covered by e2e section 3 (privileged trusted image).

## And what still gets through (be honest)

| Attacker has | Outcome |
|---|---|
| the ability to change `release.yaml` on `main` | **can release anything**: that file is the trust anchor. Protect it with branch protection and CODEOWNERS review ([runbook](../docs/runbook.md)). |
| cluster-admin | **can delete the policies**. Admission control does not defend against cluster administrators. |
| a vulnerable dependency that nobody knows about yet | ships, because no scanner can find an unknown CVE. Trivy Operator catches it once it is published. |
| a compromised build step inside the release job | the provenance is written by the same job (not SLSA Build L3, chapter 7). |

Saying this clearly is part of the design: every security control has a boundary, and the [architecture document](../docs/architecture.md) lists them under "Trust boundaries".

## Check yourself

1. Which single file, if changed by an attacker on `main`, defeats the whole system? What protects it?
2. For each of the four attackers, name the exact check that stops them.
3. Which protection works even after the image has passed every check at admission?

### Answers

<details><summary>Answers</summary>

1. `.github/workflows/release.yaml`. Production trusts its identity, so changes to it must go through branch protection with required review and CODEOWNERS.
2. Registry token: no signature from the release identity (and digest pinning). Git deploy access: Kyverno signature check on the new pods. Injected workflow: the certificate identity names the wrong workflow. Dangerous genuine image: `restricted-pods` and PSA restricted.
3. Trivy Operator with the `RunningImageHasCriticalVulnerabilities` alert: it re-scans running images for vulnerabilities published later.

</details>
