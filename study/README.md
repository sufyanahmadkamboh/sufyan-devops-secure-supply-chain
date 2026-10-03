# Study guide: learn every tool used in this project

This guide is for engineers who are **new to DevOps and to software supply chain security**. You don't need to know any of these tools before you start. Each chapter explains:

1. **What** the tool or idea is, in plain language
2. **Why** this project uses it, and the alternatives
3. **How** it works: the few concepts you really need
4. **Where** it is wired into this repository, with real file paths and snippets
5. **Try it:** commands to run against the lab cluster or the published image
6. **Common mistakes** people make with it
7. **Check yourself:** short questions (answers at the end of each chapter)

> 📄 **Prefer one file?** Download the whole guide as a single PDF: **[study-guide.pdf](study-guide.pdf)** (answers expanded, ready to print).
> Rebuild it after editing with `python study/tools/build_pdf.py`.

## How to use this guide

Read the chapters in order. Each one builds on the previous ones. Do the "Try it" sections with the lab running (`scripts/platform-up.sh`). Reading alone won't make the ideas stick; running the commands will.

| Step | Chapter | You will understand |
|---|---|---|
| 0 | [The big picture](00-big-picture.md) | What the whole project does, in 5 minutes, with no jargon |
| 1 | [Containers and images](01-containers-and-images.md) | Layers, tags vs digests, registries, distroless images |
| 2 | [Software supply chain attacks](02-supply-chain-attacks.md) | How attackers get untrusted code into production, and why "it came from our registry" proves nothing |
| 3 | [GitHub Actions security](03-github-actions-security.md) | Permissions, OIDC tokens, pinning actions, template injection, zizmor and actionlint |
| 4 | [SBOM](04-sbom.md) | The list of ingredients of an image: Syft and CycloneDX |
| 5 | [Vulnerability scanning](05-vulnerability-scanning.md) | CVEs, severities, the Trivy gate at build time and Trivy Operator at run time |
| 6 | [Signing with Sigstore](06-signing-with-sigstore.md) | cosign, keyless signing, Fulcio, Rekor, and why the identity is a workflow file |
| 7 | [Attestations and SLSA provenance](07-attestations-and-provenance.md) | Signed statements about an image: provenance, scan, SBOM |
| 8 | [Admission control with Kyverno](08-admission-control-kyverno.md) | How the cluster checks every Pod before it runs |
| 9 | [Pod security](09-pod-security.md) | Why a trusted image still needs a safe pod spec |
| 10 | [GitOps with Argo CD](10-gitops-argo-cd.md) | Git as the source of truth, and why GitOps does not have to be trusted |
| 11 | [Monitoring](11-monitoring.md) | Kyverno and Trivy Operator metrics, three alerts, promtool tests, Grafana |
| 12 | [The release pipeline](12-release-pipeline.md) | release.yaml job by job: build, e2e, promote |
| 13 | [The end-to-end attack test](13-e2e-attack-test.md) | Every attack scenario and what stops it |
| 14 | [How everything fits together](14-how-it-fits-together.md) | One release and four attackers, traced through every tool |
| 15 | [Hands-on labs](15-hands-on-labs.md) | Guided exercises, from "look around" to "break the tests" |
| | [Glossary](glossary.md) | Every term in one place |
| | [Interview questions](interview-questions.md) | 25 questions this project prepares you for, with answers |

## Before you start

You need:
- **Docker** (Docker Desktop on Windows/macOS, Docker Engine on Linux)
- **kind** (Kubernetes in Docker) and **Bash** (Git Bash works on Windows)
- About 6 GB of free memory for the lab cluster

Every other tool (kubectl, helm, cosign, crane, the Kyverno CLI) runs inside the pinned toolbox image (`tools/toolbox/Dockerfile`), so you do not install them yourself.

```bash
scripts/platform-up.sh       # kind + Kyverno + policies + Argo CD + Trivy Operator + Prometheus + Grafana
source scripts/lib.sh        # gives you the helpers tb (toolbox) and k (kubectl in the toolbox)
k get pods -A
```

The full attack test (`scripts/e2e.sh`) runs in GitHub Actions, because it needs a GitHub identity token for keyless signing and write access to the image registry. You can read its results in the Actions tab and in [docs/test-results.md](../docs/test-results.md).

## Time needed

| Part | Time |
|---|---|
| Chapters 0–3 (foundations) | 2–3 hours |
| Chapters 4–9 (the protections) | 4–5 hours |
| Chapters 10–14 (delivery, monitoring, the whole picture) | 3–4 hours |
| Labs | 3–4 hours |

## Where to go next

After this guide, read the project's [architecture document](../docs/architecture.md) (the decision log explains every trade-off), the [runbook](../docs/runbook.md) and the [troubleshooting notes](../docs/troubleshooting.md).
