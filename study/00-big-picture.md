# 0. The big picture

## The story in one paragraph

A company runs its web shop on Kubernetes. Every time a developer merges code, a pipeline builds a container image and the cluster runs it. The question this project answers is: **how does the cluster know that the image it is about to run is really the one our pipeline built from our code, and that nobody swapped it, changed it or slipped in their own?** The answer: the pipeline puts a tamper-proof seal on every image, and the cluster checks the seal before it runs anything.

## An analogy: the pharmacy

Think of a pharmacy.

- A medicine factory produces a box of tablets, **seals** it, and prints a **stamp** that says which factory made it, which batch it is and that it passed quality control.
- A truck brings the box to the pharmacy. Many people handle it on the way.
- Before handing the box to a patient, the **pharmacist checks**: is the seal intact? Is the stamp from *our* licensed factory? Did this batch pass the lab test?
- A box with a broken seal, no stamp, or a stamp from an unknown factory is **not handed out**, even if it looks right and arrived on the usual truck.

In this project:

| Pharmacy | This project |
|---|---|
| The factory | the release workflow in GitHub Actions (`.github/workflows/release.yaml`) |
| The tablets | the container image `ghcr.io/sufyanahmadkamboh/storefront-api` |
| The seal | a cryptographic **signature** tied to the image's exact content (its digest) |
| The stamp: factory, batch, lab test | signed **attestations**: provenance (which code, which workflow), vulnerability scan, ingredient list (SBOM) |
| The truck | the image registry (GHCR) and GitOps (Argo CD) |
| The pharmacist | **Kyverno**, checking every Pod at the cluster door |
| A health inspector who visits later | **Trivy Operator**, re-scanning running images for problems discovered after delivery |

The key insight: **the truck is not trusted.** The registry, the git repository and the deployment tool can all be tampered with. Only the seal and the stamp count.

## Why this matters now

Software supply chain attacks are real and frequent. In 2026 alone:

- An automated campaign pushed malicious GitHub Actions workflows into thousands of repositories within hours, to steal deployment credentials.
- Attackers moved the version tags of a popular GitHub Action to a malicious commit, so every pipeline using that tag ran the attacker's code.
- Researchers showed that insecure workflow files let outsiders hijack the pipelines of large organisations.

If an attacker gets a registry password, a deploy key, or a way into your pipeline, a normal cluster will happily run whatever they push. This project makes that fail.

## What happens on a normal release

1. A developer merges code to `main`.
2. The release workflow builds the image, **scans** it (no serious known vulnerabilities allowed), pushes it, and creates a **SBOM** (the list of everything inside).
3. It **signs** the image and **attests** the provenance, scan and SBOM, using a short-lived certificate that says "made by release.yaml on main of this repository". No secret key is stored anywhere.
4. A throwaway test cluster runs a series of **attacks** against the new image. If any attack succeeds, the release stops.
5. The workflow writes the image's exact digest into the deployment files in git.
6. **Argo CD** notices the change and asks Kubernetes to run it.
7. **Kyverno** checks the seal and the stamps, rewrites the image reference to the exact digest it verified, and only then lets the Pod start.
8. **Trivy Operator** keeps scanning running images; **Prometheus** alerts if something is blocked or a new vulnerability appears.

## What an attacker can no longer do

| The attacker has... | Result |
|---|---|
| the registry password | can push images, but they carry no valid seal → refused |
| write access to the deployment files in git | Argo CD applies the change, Kyverno refuses the pods → the old version keeps running |
| a malicious workflow injected into the repository | it can sign, but its certificate names the wrong workflow → refused |
| a fake "clean scan" document | it is not signed by the release workflow → refused |
| a genuine image, but wants to run it as root/privileged | refused by the pod security rules |

And what it does **not** protect against (honesty matters): someone who can change `release.yaml` itself on `main`, or a cluster administrator who deletes the policies. Those are protected by process (code review, branch protection, access control), described in chapter 14.

## The tools, one line each

| Tool | Job here |
|---|---|
| Docker / distroless | build a tiny image with nothing but the program |
| GitHub Actions | the build platform; its identity is the signing identity |
| Trivy | scan for known vulnerabilities (build gate) |
| Syft | produce the SBOM |
| Sigstore cosign | sign and attest, keyless |
| Kyverno | check every Pod at admission time |
| Argo CD | deploy from git (GitOps) |
| Trivy Operator | re-scan images that are already running |
| Prometheus + Grafana | alerts and dashboard |
| kind | throwaway Kubernetes clusters for the lab and the CI attack test |

## Check yourself

1. In the pharmacy analogy, who plays the pharmacist, and what exactly do they check?
2. Why is "the image came from our own registry" not enough?
3. Name two things this project does not protect against.

### Answers

<details><summary>Answers</summary>

1. Kyverno. For every Pod it checks the signature (seal) made by the release workflow, and the signed provenance, scan and SBOM attestations (stamps), before the Pod may start.
2. Anyone with the registry password (or a stolen CI token) can push images into that registry, and tags can be moved to different content. Only a signature from the trusted build identity proves who built the exact content.
3. A person who can change `release.yaml` on `main` (they control the trusted identity), and a cluster administrator who can remove the policies.

</details>
