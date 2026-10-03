# Project summary

**Zero-Trust Software Supply Chain for Kubernetes** · Senior

**What it does:** Production only runs container images that this repository's release workflow built, signed and
vouched for. Everything else is refused at admission, including images pushed with stolen registry credentials and
images signed by a different (injected) workflow.

**Release pipeline (GitHub Actions):**
- Go service built into a 3.7 MB distroless, non-root image; base images pinned by digest.
- Trivy gate: no CRITICAL or HIGH vulnerabilities.
- Pushed by digest to GHCR.
- Keyless signing with cosign (GitHub OIDC → Fulcio certificate → Rekor transparency log).
- Three signed attestations: SLSA v1 provenance, Trivy vulnerability scan, CycloneDX SBOM (Syft).
- End-to-end attack test on a fresh kind cluster; only then is the digest committed to `deploy/prod`.
- Workflow hardening: actions pinned by SHA (checked in CI), `permissions: {}` by default, no expressions in
  `run:`, zizmor and actionlint, checksum-verified tool downloads, CODEOWNERS, Dependabot.

**Admission (Kyverno 1.19, CEL policies):**
- ImageValidatingPolicy: signature identity must be `release.yaml@refs/heads/main` of this repository;
  provenance must name this repository and `main`; the signed scan must show 0 CRITICAL/HIGH; a signed SBOM must
  exist; the tag is rewritten to the verified digest.
- ValidatingPolicies: only this repository's image; controllers must pin a digest; restricted pod settings
  (non-root, no privilege, read-only root, dropped capabilities, limits).
- `prod` enforces, `sandbox` runs the same policies in audit mode (PolicyReports).

**Runtime:**
- Argo CD syncs `deploy/prod` (GitOps; treated as untrusted for security).
- Trivy Operator re-scans running images.
- Prometheus alerts: untrusted workload blocked, running image with CRITICAL CVEs, admission controller down.
  Unit-tested with promtool. Grafana dashboard as code.

**Measured (GitHub Actions, fresh cluster per release):**
- Foreign image refused in 0.5 s, unsigned 2.1 s, tampered 2.0 s, imposter-signed 2.0 s, privileged 0.4 s.
- Malicious git commit: applied by Argo CD, refused by the cluster 6 s after the push; production kept serving.
- Old image with known CVEs: VulnerabilityReport plus a firing alert.

**Stack:** Go 1.27, Docker, cosign 3.1, Syft 1.54, Trivy 0.75, Kyverno 1.19, Argo CD 3.5, Trivy Operator 0.34,
Prometheus 3.15, Grafana 13.2, kind, Kustomize, GitHub Actions, GHCR.
