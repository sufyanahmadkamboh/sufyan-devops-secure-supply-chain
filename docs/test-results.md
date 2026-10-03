# Test results

All numbers on this page were measured. The end-to-end figures come from release run
[37119604685](https://github.com/sufyanahmadkamboh/sufyan-devops-secure-supply-chain/actions/runs/37119604685) on a GitHub-hosted
`ubuntu-latest` runner. Each release builds a new kind cluster (Kubernetes 1.37, one control plane and one worker)
and runs `scripts/e2e.sh` against the digest it just signed. The step summary of every release run repeats these
results, and the raw report of this run is in [e2e-results-37119604685.md](e2e-results-37119604685.md).

Timings are wall-clock from the test script. "Refused in N ms" is the time from `kubectl create` until the API
server returned the denial. That includes Kyverno fetching the signatures and attestations from GHCR and checking
the certificate against Rekor.

The next release, [37132754826](https://github.com/sufyanahmadkamboh/sufyan-devops-secure-supply-chain/actions/runs/37132754826)
(after the monitoring and policy fixes listed at the end of this page), passed every check again with similar
timings: refusals in 359–2,007 ms, GitOps attack refused 5 s after the push, CVE alert firing 322 s after the report.

## 1. Platform

| Check | Result |
|---|---|
| kind + Kyverno + policies + Argo CD + Trivy Operator + Prometheus/Grafana | up in **156 s** |

## 2. Legitimate release through GitOps

| Check | Result |
|---|---|
| Argo CD syncs the digest signed minutes earlier | 2/2 pods on the verified digest after **18 s** |
| Service answers | `{"commit":"4ea3158dad4c…","version":"0.1.9"}` |

## 3. Attacks at the cluster door

The attacker images are pushed into the **real** repository `ghcr.io/sufyanahmadkamboh/storefront-api` with the
job's token. That simulates a stolen registry credential: the registry accepts them, so only the cluster can say no.

| Attack | Result | Refused by |
|---|---|---|
| Foreign registry image (`docker.io/library/nginx`) | **refused in 484 ms** | `allowed-images` |
| Unsigned image in the trusted repository | **refused in 2,058 ms** | `verify-release-images`: no signatures found |
| Tampered copy of the trusted image (one extra layer) | **refused in 1,968 ms** | `verify-release-images`: the new digest has no signature |
| Tampered image **signed and attested** by a different workflow of the same repository (`e2e.yaml`), with forged SLSA provenance and a clean forged scan | **refused in 1,970 ms** | `verify-release-images`: certificate identity `…/e2e.yaml@refs/heads/main` is not `…/release.yaml@refs/heads/main` |
| Trusted image in a privileged container | **refused in 363 ms** | Pod Security `restricted` (API server, before Kyverno) |
| Control: trusted image with a safe pod spec | **admitted in 4,002 ms** | — |

The imposter signature is real: the test checks with `cosign verify` that it is a valid Sigstore signature, with a
Fulcio certificate and a Rekor entry, before it tries to deploy. This is the injected-workflow scenario: an attacker
who can add a workflow to the repository can sign, but not as the release workflow.

## 4. Attack through GitOps

A commit to a temporary branch that Argo CD follows replaces the prod digest with the imposter-signed image.

| Check | Result |
|---|---|
| Argo CD picks up the malicious commit and applies it | after 4 s |
| Kyverno refuses the Deployment update | **6 s after the push** (Argo CD sync result shows `Policy verify-release-images failed`) |
| Production during the attack | still only the trusted digest; service answered |
| Revert commit synced | after **5 s** |
| Alert `UntrustedWorkloadBlocked` | **firing** when checked right after the attack (rule looks back 10 min) |

## 5. Sandbox: audit mode and continuous scanning

| Check | Result |
|---|---|
| Unsigned image in `sandbox` (audit policies) | allowed to run |
| PolicyReports | violations listed **18 s** later (`restricted-pods-audit`, `verify-release-images-audit`) |
| Trivy Operator scans a running `nginx:1.21.0` | report after **90 s**: **27 CRITICAL** vulnerabilities |
| Alert `RunningImageHasCriticalVulnerabilities` | **firing 321 s** after the report (rule has `for: 5m`) |

## 6. Monitoring health

| Check | Result |
|---|---|
| Firing alerts at the end | `RunningImageHasCriticalVulnerabilities`, `UntrustedWorkloadBlocked` (both expected) |
| `AdmissionControllerDown` | not firing |

## Release pipeline (build job)

| Check | Result |
|---|---|
| Image size | 3.7 MB (distroless static, non-root) |
| Trivy gate (CRITICAL/HIGH) | 0 findings |
| Signature + 3 attestations | verified by the build job with the cluster's identity rule |
| Evidence | `supply-chain-evidence` artifact: SBOM (CycloneDX), scan report, provenance |
| Promote | commit `deploy: storefront-api 38b5a66e735e` to `deploy/prod` by the release job, after the attack test passed |

## Static checks (`ci.yaml`, every push)

| Check | Result |
|---|---|
| Every `uses:` pinned to a 40-character SHA | pass |
| actionlint 1.7.12, zizmor 1.30.1 | 0 findings (one documented `self-repository` ignore) |
| `go vet`, `go test -race` | 5 tests pass |
| ShellCheck, hadolint 2.15.1, yamllint 1.38.0 `--strict` | clean |
| `kyverno test` | 12 / 12 pass (incl. look-alike repository, tag vs digest, unsafe pod, pod- vs container-level `runAsNonRoot`) |
| promtool check rules + unit tests | pass (5 test groups, incl. a counter that appears already above 0, and a Prometheus restart) |

## Experiments that shaped the design

These were run on a local kind cluster with the same versions (Kyverno 1.19.1, cosign 3.1.3).

| Experiment | Observation | Decision |
|---|---|---|
| Image signed with cosign 3 defaults (new Sigstore bundle format) | Kyverno ImageValidatingPolicy: `failed to verify cosign signatures: no signatures found` | sign with `--new-bundle-format=false --use-signing-config=false` (classic `.sig` / `.att`) |
| Same image signed in the classic format | admitted; image rewritten to the digest | keep classic format until Kyverno reads bundles |
| Attestor without `ctlog.url` | `getting Rekor public keys: rekor URL must be provided` | set `https://rekor.sigstore.dev` |
| Kyverno metric for denials | `kyverno_policy_results_total` absent for refused admissions; `kyverno_admission_requests_total{request_allowed="false"}` present | alert on the latter |
| Webhook failure policy | all Kyverno resource webhooks report `failurePolicy: Fail` | fail closed is the default |
| Trivy Operator on `nginx:1.21.0` (local) | 27 CRITICAL, 134 HIGH | used as the "known bad running image" |
| Local demo: new denials right after a Kyverno restart | counter series created at 3; `increase()` = 0; `UntrustedWorkloadBlocked` silent | rule also counts series younger than 10 min (promtool test added); confirmed firing on the live cluster |
| Local demo: 9 unsigned + 10 foreign-image attempts | metric showed 10 refusals: the unsigned ones were counted under `MutatingWebhookConfiguration`, which the rule filtered out | rule and dashboard count both phases (a request is refused in one phase only); promtool test includes a mutating-phase refusal |
| Local demo: trusted image, `runAsNonRoot` only at pod level | refused by `restricted-pods` although valid Kubernetes and PSA-compliant | policy follows pod/container inheritance; 2 test cases added; confirmed admitted on the live cluster |

## Reproduce

The attack test is built to run in GitHub Actions: the imposter scenario needs the keyless identity of the
`e2e.yaml` workflow, and the test pushes attacker images and a temporary branch. To reproduce it in a fork:
1. Change the image name and the trusted identity in `policies/base/*.yaml`, `scripts/e2e.sh` (`IMAGE`) and
   `.github/workflows/release.yaml`.
2. Push to `main`. The release workflow builds, signs, runs the attack test and promotes.

The platform itself runs locally with `scripts/platform-up.sh`, and the admission checks can be tried by hand with
the commands in the [README](../README.md#8-quick-start).
