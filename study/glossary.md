# Glossary

| Term | Meaning |
|---|---|
| **actionlint** | a linter for GitHub Actions workflow files (syntax, expressions, shell problems) |
| **admission controller** | code in the Kubernetes API server that accepts, changes or refuses objects before they are stored |
| **admission webhook** | an external service (here Kyverno) that the API server calls during admission |
| **Argo CD** | a GitOps controller that keeps a cluster equal to manifests in git |
| **attestation** | a signed statement about an artifact (provenance, scan, SBOM), usually an in-toto statement |
| **Audit (validationAction)** | allow the request but record the violation in a PolicyReport |
| **base image** | the image a Dockerfile starts `FROM` |
| **CEL** | Common Expression Language; the expression language of Kyverno's new policy types and of Kubernetes itself |
| **certificate identity / subject** | in keyless signing, who the certificate was issued to; here a workflow file and git ref |
| **CODEOWNERS** | a GitHub file that names who must review changes to given paths |
| **cosign** | Sigstore's command-line tool for signing and verifying images and attestations |
| **CVE** | Common Vulnerabilities and Exposures: the public ID of a known security hole |
| **CycloneDX** | a standard SBOM format (also used for other bills of materials) |
| **Deny (validationAction)** | refuse a request that violates the policy |
| **Dependabot** | GitHub's service that opens pull requests to update dependencies, pinned SHAs and digests |
| **digest** | the SHA-256 hash of an image manifest (`sha256:...`); changes if any byte changes; cannot be moved |
| **distroless** | images with only the app and its runtime files: no shell, no package manager |
| **e2e (end-to-end) test** | a test of the whole system as a user or attacker would use it; here `scripts/e2e.sh` |
| **Fulcio** | Sigstore's certificate authority; issues short-lived certificates for an OIDC identity |
| **GHCR** | GitHub Container Registry, `ghcr.io` |
| **GitOps** | managing the desired state of a system as files in git, applied by a controller |
| **Grafana** | dashboards over Prometheus and other data sources |
| **headless Service** | a Kubernetes Service without a cluster IP; DNS returns the pod IPs directly |
| **ImageValidatingPolicy** | Kyverno 1.19 policy kind that verifies image signatures and attestations with CEL |
| **in-toto statement** | the standard envelope of an attestation: subject (digest), predicateType, predicate |
| **keyless signing** | signing with a short-lived certificate bound to an identity, instead of a long-lived private key |
| **kind** | "Kubernetes in Docker": runs throwaway clusters as Docker containers |
| **Kustomize** | builds Kubernetes YAML from a base plus overlays and patches (`kubectl kustomize`) |
| **Kyverno** | a Kubernetes policy engine running as an admission webhook |
| **layer** | one file-system change set of an image; images are stacks of layers |
| **least privilege** | give each job, user or pod only the permissions it needs |
| **manifest (image)** | the JSON document listing an image's config and layers; its hash is the digest |
| **maxUnavailable / maxSurge** | rolling-update settings: how many pods may be missing / extra during a rollout |
| **mutateDigest** | Kyverno option that rewrites an image reference to the digest it verified |
| **NetworkPolicy** | Kubernetes rules for which traffic may reach or leave pods |
| **OIDC (OpenID Connect)** | a standard for identity tokens; GitHub Actions issues one per job when `id-token: write` is granted |
| **persist-credentials** | `actions/checkout` option; `false` keeps the token out of `.git/config` |
| **pinning** | referring to an exact, unchangeable version: a commit SHA for actions, a digest for images |
| **Pod Security Admission (PSA)** | built-in Kubernetes admission that enforces a Pod Security Standard per namespace |
| **Pod Security Standards** | `privileged`, `baseline`, `restricted`: three levels of pod restrictions |
| **PolicyReport** | a Kyverno resource listing policy results (pass/fail) for resources in a namespace |
| **predicate** | the content part of an in-toto statement (the provenance, the scan result, the SBOM) |
| **promote** | the release job that writes the tested digest into `deploy/prod` |
| **promtool** | Prometheus's CLI; checks rule files and runs alert unit tests |
| **Prometheus** | a metrics system: scrapes metrics, stores time series, evaluates alert rules |
| **PromQL** | Prometheus's query language |
| **provenance** | a record of how an artifact was built: source, commit, build process, run |
| **registry** | a server that stores and serves container images |
| **Rekor** | Sigstore's public, append-only transparency log of signatures |
| **reusable workflow** | a GitHub workflow called by another with `uses:`; runs with its own file identity |
| **SBOM** | Software Bill of Materials: the list of components inside a piece of software |
| **seccomp** | a Linux kernel feature that limits which system calls a process may make |
| **selfHeal / prune** | Argo CD options: undo manual changes / delete objects removed from git |
| **severity** | how bad a vulnerability is: LOW, MEDIUM, HIGH, CRITICAL |
| **Sigstore** | an open-source project for signing software (cosign, Fulcio, Rekor) |
| **SLSA** | Supply-chain Levels for Software Artifacts: a framework and a provenance format |
| **Syft** | a tool that generates SBOMs from images and directories |
| **tag** | a human-friendly, movable name for an image (`:1.2.3`, `:latest`) |
| **template injection** | untrusted text (a PR title, a branch name) expanded by `${{ }}` into a workflow's shell script |
| **transparency log** | a public, append-only, verifiable log; anyone can check that an entry exists and was not changed |
| **Trivy** | an open-source vulnerability scanner |
| **Trivy Operator** | runs Trivy inside a cluster and keeps scanning running workloads |
| **trust anchor** | the one thing everything else relies on; here the identity `release.yaml@refs/heads/main` |
| **ValidatingPolicy** | Kyverno 1.19 policy kind that validates resources with CEL |
| **VulnerabilityReport** | the Trivy Operator resource holding the scan result of one workload |
| **zizmor** | a static analyser for security problems in GitHub Actions workflows |
