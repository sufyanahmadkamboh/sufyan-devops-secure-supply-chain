# Troubleshooting

Everything here was hit while building and testing this project.

## Signatures and verification

**Kyverno: "failed to verify cosign signatures: no signatures found" for an image cosign signed fine**
cosign 3 writes signatures in the new Sigstore *bundle* format by default (stored as OCI referrers / a
`sha256-<digest>` tag). Kyverno 1.19's ImageValidatingPolicy did not find them in testing, while classic
signatures (`.sig` / `.att` tags) verified. The pipeline signs with
`--new-bundle-format=false --use-signing-config=false`.

**cosign: "--tlog-upload=false is not supported with --signing-config"**
cosign 3 uses a signing config by default. For key-based local experiments without the transparency log, add
`--use-signing-config=false`.

**Kyverno: "getting Rekor public keys: rekor URL must be provided"**
When the transparency log is not ignored, the attestor needs `ctlog.url: https://rekor.sigstore.dev`.

**Kyverno: "failed to evaluate policy: no such key: result"**
`extractPayload(image, attestations.x)` returns the whole in-toto statement. The data is under `.predicate`
(for example `extractPayload(...).predicate.scanner.result`).

**"kyverno.io/v1 ClusterPolicy is deprecated"**
Kyverno 1.19 deprecates ClusterPolicy in favour of the CEL-based policy types. This project uses
ImageValidatingPolicy and ValidatingPolicy only.

## Cluster

**Policies rejected with "failed calling webhook validate-policy.kyverno.svc … connection refused"**
`helm --wait` returns before Kyverno's webhook serves requests. `platform-up.sh` retries the apply until it is
accepted.

**Trivy Operator target "connection refused" in Prometheus**
The `trivy-operator` service is headless (`clusterIP: None`), so its DNS name resolves to the pod, where the
metrics port is 8080, not the service port 80. Scrape `trivy-operator.trivy-system.svc:8080`.

**Test pods rejected in prod although the image is trusted**
The prod namespace also enforces the Kubernetes Pod Security "restricted" level, which requires
`seccompProfile: RuntimeDefault`. Without it, the API server refuses the pod before Kyverno looks at it.

**Argo CD shows "SyncFailed" with "Policy verify-release-images failed"**
The image policy also covers pod controllers (Deployments, ReplicaSets, StatefulSets, ...), so Kyverno refuses
the Deployment update itself and Argo CD reports the refusal in its sync result. The old ReplicaSet keeps
running. In GitOps this is the intended result: git said "run this", the cluster said no. Look at
`kubectl -n argocd get application storefront-api -o jsonpath='{.status.operationState.syncResult.resources}'`.
If a controller was admitted some other way, the pod creation is refused instead:
`kubectl -n prod get events --field-selector reason=FailedCreate`.

## CI

**zizmor suggests `uses: $/.github/workflows/e2e.yaml`, actionlint rejects it**
The self-repository syntax is new (GitHub, July 2026) and actionlint 1.7.12 cannot parse it yet. The workflow
keeps `./` with a documented `zizmor: ignore[self-repository]`. No earlier step in that job could plant files.

**hadolint DL3003 (`cd` inside RUN)**
Use `WORKDIR` or absolute paths. The toolbox Dockerfile removes its temp directory with an absolute path.

**`crane copy -q`: unknown shorthand flag**
crane has no quiet flag; redirect its output instead.

**Kyverno metric for denials**
In Kyverno 1.19, denials appear in `kyverno_admission_requests_total{request_allowed="false"}`, and
image-policy outcomes appear in `kyverno_image_validating_policy_results_total`. The alert rules use these, as
checked against a live cluster. Do not filter on `request_webhook`: signature failures are refused in the
mutating phase (the image policy rewrites tags to digests), registry and pod-spec failures in the validating
phase.

## Monitoring

**`UntrustedWorkloadBlocked` did not fire for the first refusals**
Kyverno creates a counter series only on the first refusal of a kind, and the series starts at that value.
`increase()` needs two samples, so it does not see that first step. The rule also counts series that did not exist
10 minutes ago (skipped while Prometheus itself is younger than 10 minutes). Covered by a promtool test.

**A pod with `runAsNonRoot: true` in the pod securityContext was refused by `restricted-pods`**
Fixed: the policy now follows Kubernetes semantics (the container's value wins, otherwise the pod's). A container
that sets `runAsNonRoot: false` is still refused. Both cases are in `policies/tests`.

## Windows (Git Bash)

Docker needs `C:/` paths when `MSYS_NO_PATHCONV=1` is set: `scripts/lib.sh` uses `pwd -W`. All CLIs run in the
toolbox container, so nothing but Docker, kind and Bash is needed on the host.
