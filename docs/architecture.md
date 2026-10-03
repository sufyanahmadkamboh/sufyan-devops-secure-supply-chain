# Architecture

## The idea in one sentence

Production does not trust *where an image came from* (a registry, a tag, a git commit). It trusts **cryptographic
proof that this repository's release workflow built it**. That proof is checked at the cluster door, for every Pod.

## Flow

```
 git push main ──► release.yaml (GitHub-hosted runner, identity = release.yaml@refs/heads/main)
                     1. docker build (unit tests inside, base images pinned by digest, static non-root binary)
                     2. Trivy gate: no fixable CRITICAL/HIGH ──► fail = nothing is published
                     3. push to ghcr.io/sufyanahmadkamboh/storefront-api  (by digest)
                     4. Syft SBOM (CycloneDX) · Trivy report (cosign-vuln) · SLSA v1 provenance
                     5. cosign keyless: GitHub OIDC token ──► Fulcio short-lived certificate ──► Rekor log entry
                        sign the digest + attest SBOM, scan and provenance (4 signed objects next to the image)
                     6. verify the published signatures with the same identity rule as the cluster
                     7. e2e.yaml: throwaway kind cluster, the attacks in docs/test-results.md must all be blocked
                     8. promote: commit the digest to deploy/prod (only after 7 passed)
                                          │
 Argo CD (in the cluster) ◄──── git ──────┘  syncs deploy/prod
        │ kubectl apply (Deployment ─► ReplicaSet ─► Pod)
        ▼
 Kubernetes API ──► Kyverno admission webhook (namespace label supply-chain.sufyan.dev/enforce=true)
                     • allowed-images: only ghcr.io/sufyanahmadkamboh/storefront-api; workloads pinned by digest
                     • restricted-pods: non-root, no privilege escalation, drop ALL, read-only root, limits
                     • verify-release-images: signature by release.yaml@main (Fulcio cert + Rekor),
                       provenance says this repo + main, signed scan has no CRITICAL/HIGH, signed SBOM exists;
                       rewrites the image to the verified digest
        ▼
 Pod runs ─► Trivy Operator re-scans running images (new CVEs) ─► Prometheus ─► alerts + Grafana
```

## Components

| Component | Version | Role |
|---|---|---|
| GitHub Actions | — | build platform; its OIDC identity is the signing identity |
| Sigstore cosign | 3.1.3 | keyless signing and attestations (Fulcio CA, Rekor transparency log) |
| Syft | 1.54.0 | SBOM (CycloneDX) |
| Trivy | 0.75.0 | build-time vulnerability gate and signed scan report |
| Kyverno | 1.19.1 | admission control: ImageValidatingPolicy + ValidatingPolicy (CEL) |
| Argo CD | 3.5.3 | GitOps delivery of deploy/prod |
| Trivy Operator | 0.34.0 | continuous scanning of running workloads, Prometheus metrics |
| Prometheus / Grafana | 3.15.0 / 13.2.3 | alerts (promtool-tested) and dashboard |
| kind | 0.33.0 (Kubernetes 1.37) | throwaway clusters for the lab and the CI attack test |

## Namespaces and modes

| Namespace label | Policies | Effect |
|---|---|---|
| `supply-chain.sufyan.dev/enforce: "true"` (prod) | `*` (validationActions: Deny) | violations are refused |
| `supply-chain.sufyan.dev/audit: "true"` (sandbox) | `*-audit` (Audit) | allowed, reported in PolicyReports |

The two modes come from one Kustomize base (`policies/base`) with two overlays, so the rules can never drift
apart. Rolling a new rule out: add it to base, watch the sandbox reports, then rely on prod.

## Trust boundaries (what an attacker needs, and what stops them)

| Attacker has | Can they run code in prod? | Why not |
|---|---|---|
| a registry token (push to GHCR) | no | pushed images have no signature from release.yaml@main |
| write access to `deploy/prod` (git) | no | Argo CD applies it, Kyverno refuses the pods; old pods keep serving |
| a malicious workflow file added to the repo (Megalodon-style) | no | its keyless certificate names *that* workflow, not release.yaml |
| a forged provenance/scan document | no | attestations must be signed by the release identity |
| a trusted image but a dangerous pod spec | no | restricted-pods (and Kubernetes Pod Security "restricted") |
| ability to change `release.yaml` on main | **yes** | this is the trust anchor: protect it with branch protection + CODEOWNERS review (runbook) |
| cluster-admin | **yes** | can delete the policies; admission control is not a defence against cluster admins |

## Decision log

| # | Decision | Why | Trade-off |
|---|---|---|---|
| 1 | Keyless signing (GitHub OIDC + Fulcio + Rekor) | no private key to store, leak or rotate; identity = workflow file + ref; every signature is publicly logged | depends on public Sigstore services (can be self-hosted) |
| 2 | Trust **release.yaml@refs/heads/main**, not "any workflow of the repo" | a second, injected workflow (Megalodon) or a PR branch cannot produce trusted signatures | moving/renaming the workflow changes the identity (policy update needed) |
| 3 | cosign "classic" signature format (`--new-bundle-format=false`) | tested: Kyverno 1.19 ImageValidatingPolicy verifies classic `.sig/.att` signatures but finds no signatures in cosign 3's new bundle format | revisit when Kyverno reads Sigstore bundles |
| 4 | ImageValidatingPolicy / ValidatingPolicy (CEL), not ClusterPolicy | ClusterPolicy is deprecated in Kyverno 1.19 | newer API, fewer examples |
| 5 | Vulnerability rule reads the *signed* scan | an attacker cannot hand Kyverno a clean report: it must be signed by the release identity | the scan is from build time; new CVEs are caught by Trivy Operator |
| 6 | Digest pinning in git **and** `mutateDigest` at admission | tags are mutable; what was verified is exactly what runs | the promote job must commit each digest |
| 7 | Promote only after the e2e attack test passes | a release that weakens the defences never reaches deploy/prod | slower releases (≈15 min) |
| 8 | Install CLI tools by checksum instead of third-party actions | fewer third-party actions = smaller CI supply chain; every remaining action pinned to a commit SHA (enforced by a script) | update checksums by hand / Dependabot |
| 9 | zizmor + actionlint + pinned-actions check in CI | the 2025–2026 attacks used workflow weaknesses (template injection, moved tags) | — |
| 10 | Distroless static non-root image, 3.7 MB | almost nothing to exploit or to patch; 0 findings at build time | no shell for debugging (use ephemeral containers) |
| 11 | Sandbox in audit mode | lets teams see what *would* be blocked before enforcing | needs someone to read the reports |
| 12 | Trivy Operator for running images | build-time scans age; a CVE published tomorrow is invisible to today's pipeline | scan jobs cost CPU/memory in the cluster |
| 13 | Separate e2e.yaml (reusable) for the attack test | its jobs sign with the e2e.yaml identity, which makes the imposter scenario real | — |
| 14 | Provenance written by the build job and signed (SLSA v1 format) | binds commit, workflow and run to the digest under the release identity | not SLSA Build L3 (the build and signing run in the same job); see future improvements |
