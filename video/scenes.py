"""The video: scenes, visuals and narration.

Each scene has a title, a body (HTML from components.py) and steps. A step is one narration segment; elements with
data-s=<n> appear at step n. `hl` highlights code lines (1-based, inclusive) in the scene's code panel. `tts` overrides
the spoken text when the caption spelling would be read badly (the caption always shows `say`).
All numbers are from release run 37119604685 (docs/test-results.md) unless stated otherwise.
"""

from __future__ import annotations

from components import arrow, box, card, checklist, code, grid, label, notes, svg, terminal, tile


def S(say: str, hl: tuple[int, int] | None = None, tts: str | None = None) -> dict:
    return {"say": say, "hl": hl, "tts": tts}


REPO = "github.com/sufyanahmadkamboh/sufyan-devops-secure-supply-chain"

SCENES: list[dict] = []


def scene(chapter: str | None, kicker: str, title: str, body: str, steps: list[dict], layout: str = "full") -> None:
    SCENES.append({"chapter": chapter, "kicker": kicker, "title": title, "body": body, "steps": steps, "layout": layout})


# ---------------------------------------------------------------- 0. Hook
scene("The question", "Kubernetes supply chain security", "Could a stolen password run code in your cluster?", svg(
    box(0, 40, 60, 470, 250, "🔑", "Stolen registry token", ["leaked in a CI log,", "a laptop, a chat…"], "bad", "#2a1520")
    + arrow(0, 515, 185, 640, 185, "bad")
    + box(0, 650, 60, 420, 250, "📦", "Your registry", ["accepts the push:", "the token is valid"], "amber")
    + arrow(1, 1075, 185, 1200, 185, "bad")
    + box(1, 1210, 60, 470, 250, "☸️", "Production cluster", ["runs it: \"it came from", "our registry\""], "bad", "#2a1520")
    + label(1, 1445, 360, "😱 attacker code in prod", 32, "bad", "middle", 900)
    + box(2, 300, 430, 1120, 150, "🛡️", "This project: prove where every image came from", ["only code signed by YOUR release pipeline may run"], "ok", "#0f2a22")
    + label(3, 860, 660, "7 attacks on every release · 6 refused · 1 caught by an alert", 34, "ok", "middle", 900)
), [
    S("If someone stole your container registry password tonight, could they run their own code in your production Kubernetes cluster?"),
    S("For most teams, the honest answer is yes. The cluster runs whatever image sits in the company registry, because the token was valid."),
    S("In this video I will show you a project that changes that answer to no. Production only runs code that it can prove came from your own release pipeline."),
    S("And I do not just claim it. I attack it seven different ways on every single release, and I will show you the measured results."),
    S("By the end, you will understand every tool in this setup: what it does, how it is configured, and how to roll it out in a real production cluster. "
      "Everything is open source, and the full code and a free study guide are linked in the description."),
])

# ---------------------------------------------------------------- 1. Map
scene(None, "What you will learn", "One project, twelve tools, one goal", grid([
    card(0, "⚠️", "The problem", "real attacks from 2025 and 2026", "bad"),
    card(1, "💡", "The idea", "proof that travels with the image", "amber"),
    card(1, "🗺️", "Architecture", "from git push to running pod"),
    card(2, "🐳", "Docker + distroless", "small, non-root, pinned"),
    card(2, "⚙️", "GitHub Actions", "the hardened release pipeline"),
    card(2, "🔍", "Trivy", "scan gate + signed report"),
    card(2, "🧾", "Syft", "software bill of materials"),
    card(2, "📜", "SLSA provenance", "where and how it was built"),
    card(2, "🔏", "Sigstore cosign", "keyless signatures"),
    card(3, "🛂", "Kyverno", "admission control"),
    card(3, "🐙", "Argo CD + Kustomize", "GitOps delivery"),
    card(3, "📊", "Trivy Operator · Prometheus · Grafana", "watch what runs"),
    card(3, "🧪", "kind", "an attack test on every release"),
    card(4, "📈", "Measured results", "from real CI runs", "ok"),
    card(4, "💻", "Hands-on lab", "run and attack it on your laptop", "ok"),
    card(4, "🚀", "Production rollout", "step-by-step plan", "ok"),
], cols=4, gap=16), [
    S("Here is what we will cover. First, why this problem matters, with real attacks from 2025 and 2026."),
    S("Then the idea behind the solution, and the architecture."),
    S("Then every tool, one by one. Docker and distroless images. GitHub Actions. Trivy. Syft. SLSA provenance. And Sigstore cosign.",
      tts="Then every tool, one by one. Docker and distroless images. GitHub Actions. Trivy. Syft. S L S A provenance. And Sigstore cosign."),
    S("Kyverno for admission control. Argo CD and Kustomize for GitOps. Trivy Operator, Prometheus and Grafana for monitoring. "
      "And kind, for an end to end attack test that runs on every release."),
    S("Finally, the measured results, a hands-on lab where you run and attack the whole platform on your own laptop, "
      "and a step by step plan to use this in your own production cluster."),
])

# ---------------------------------------------------------------- 2. Problem
scene("Why: the problem", "The problem", "A registry proves who pushed, not what was built", grid([
    card(0, "📦", "Registry = a shelf", "it only proves that someone with a valid token pushed an image", "amber"),
    card(1, "❓", "Not proven", "that your reviewed code went in, or that your pipeline built it", "amber"),
    card(1, "🔍", "Scanning is not enough", "the image that runs is not always the image that was scanned", "amber"),
    card(2, "🏷️", "2025: moved tags", "tj-actions/changed-files tags pointed to a malicious commit; CI secrets leaked", "bad"),
    card(3, "🦈", "2026: injected workflows", "Megalodon: malicious workflow files pushed to 5,500+ repositories in about 6 hours", "bad"),
    card(4, "🔑", "Every day: leaked tokens", "push any image under your image's name", "bad"),
], cols=3), [
    S("Let us start with the problem. A Kubernetes cluster normally trusts any image it can pull from your registry. "
      "But a registry only proves one thing: that someone with a valid token pushed an image."),
    S("It does not prove that your reviewed code went into that image, or that your pipeline built it. "
      "And a vulnerability scan in your pipeline does not help either, if the image that runs is not the image that was scanned."),
    S("Attackers know this. In 2025, the version tags of a popular GitHub Action, tj-actions changed files, were moved to a malicious commit. "
      "Thousands of pipelines ran the attacker's code and leaked their secrets.",
      tts="Attackers know this. In 2025, the version tags of a popular GitHub Action, T J actions changed files, were moved to a malicious commit. "
          "Thousands of pipelines ran the attacker's code and leaked their secrets."),
    S("In 2026, the Megalodon campaign pushed malicious workflow files into more than five thousand repositories in about six hours. "
      "Those workflows ran with each repository's own identity."),
    S("And the simplest attack of all is a leaked registry token. With it, anyone can push an image under the same name as yours. "
      "So the real question is: how can the cluster know where an image really came from?"),
])

# ---------------------------------------------------------------- 3. Idea
scene("The idea", "The idea", "Treat images like sealed medicine", svg(
    box(0, 610, 10, 500, 170, "💊", "The container image", ["+ a seal and 3 signed documents"], "amber", "#2b2410")
    + box(1, 20, 230, 400, 190, "🔏", "Seal", ["signature made by", "OUR release workflow"])
    + box(2, 450, 230, 400, 190, "📜", "Origin certificate", ["SLSA provenance:", "repo, branch, commit"])
    + box(3, 880, 230, 400, 190, "🧪", "Lab test", ["signed vulnerability", "scan: 0 critical/high"])
    + box(4, 1310, 230, 400, 190, "🧾", "Ingredient list", ["signed SBOM: every", "library inside"])
    + box(5, 360, 500, 1000, 200, "🧑‍⚕️", "The pharmacist: Kyverno", ["checks the seal and all 3 documents before any pod starts.",
                                                                     "No valid papers → no pod. Whoever pushed it."], "ok", "#0f2a22")
), [
    S("Here is the idea. Think of a pharmacy. A pharmacist does not hand out a medicine just because it is on the shelf. "
      "They check the factory seal and the paperwork first."),
    S("We do the same with container images. Every image our pipeline builds gets a seal: a cryptographic signature, made by our release workflow."),
    S("Plus three signed documents. First, an origin certificate, called provenance, that says which repository, branch and commit it was built from."),
    S("Second, a lab test: a signed vulnerability scan."),
    S("Third, an ingredient list: a software bill of materials, or SBOM, that lists every library inside the image."),
    S("At the door of the cluster sits the pharmacist: Kyverno. Before any pod starts, it checks the seal and all three documents. "
      "No valid papers, no pod. It does not matter who pushed the image, or how it got into git."),
])

# ---------------------------------------------------------------- 4. Architecture
scene("Architecture", "Architecture", "From git push to running pod", svg(
    box(0, 0, 0, 300, 150, "🔀", "Merge to main", ["reviewed pull request"])
    + arrow(1, 305, 75, 375, 75)
    + box(1, 380, 0, 520, 320, "⚙️", "release.yaml (GitHub Actions)", ["1 build + unit tests", "2 Trivy gate", "3 push by digest → GHCR"], "blue", "#16306a")
    + label(2, 404, 220, "4 SBOM · scan · provenance", 23, "#ffe9b0")
    + label(2, 404, 252, "5 keyless sign → Fulcio + Rekor", 23, "#ffe9b0")
    + label(3, 404, 290, "6 attack test (kind) → 7 promote", 23, "#ffe9b0")
    + arrow(1, 905, 75, 985, 75)
    + box(1, 990, 0, 330, 170, "📦", "GHCR", ["image by digest", "+ .sig + 3 attestations"])
    + box(2, 1360, 0, 340, 170, "🌐", "Sigstore", ["Fulcio: certificate", "Rekor: public log"], "violet")
    + arrow(3, 640, 325, 640, 400, label="commit digest")
    + box(3, 380, 405, 520, 130, "📁", "git: deploy/prod", ["kustomization pins the digest"])
    + arrow(4, 905, 470, 985, 470)
    + box(4, 990, 405, 330, 130, "🐙", "Argo CD", ["applies deploy/prod"])
    + arrow(5, 1155, 540, 1155, 590)
    + box(5, 760, 595, 790, 140, "🛂", "Kyverno admission → pod runs", ["checks signature, provenance, scan, SBOM, pod safety"], "ok", "#0f2a22")
    + box(6, 0, 405, 340, 330, "📊", "Watch", ["Trivy Operator re-scans", "running images", "Prometheus alerts", "Grafana dashboard"], "amber")
), [
    S("Here is the whole architecture. It starts when a reviewed pull request is merged to the main branch."),
    S("The release workflow in GitHub Actions builds the image, runs the unit tests, scans it, and pushes it to the GitHub container registry, by digest."),
    S("Then it creates the SBOM, the scan report and the provenance, and signs everything with Sigstore. There is no private key anywhere. "
      "GitHub vouches for the workflow's identity, and every signature is written to a public log called Rekor."),
    S("Next, an end to end test creates a brand new Kubernetes cluster and attacks the new release. "
      "Only if every attack fails does the pipeline commit the new image digest to the production folder in git."),
    S("Argo CD sees that commit and applies it to the cluster."),
    S("Every pod passes through Kyverno, which verifies the signature and the three documents. Only then does the pod run."),
    S("And because new vulnerabilities are published every day, Trivy Operator keeps scanning the running images, "
      "while Prometheus and Grafana alert on blocked attempts and new critical issues."),
])

# ---------------------------------------------------------------- 5. Docker
DOCKERFILE = """# Base images are pinned by digest: a tag can be moved, a digest cannot.
FROM golang:1.27.1-trixie@sha256:3b77fc61…275ed5 AS build
WORKDIR /src
COPY go.mod ./
COPY *.go ./
ARG VERSION=dev
ARG COMMIT=unknown
# Static, reproducible binary: no cgo, no local paths, no build id.
RUN go test ./... \\
 && CGO_ENABLED=0 go build -trimpath -buildvcs=false \\
      -ldflags="-s -w -buildid= -X main.version=${VERSION}" \\
      -o /out/storefront-api .

# No shell, no package manager, runs as uid 65532.
FROM gcr.io/distroless/static-debian13:nonroot@sha256:e2e927ec…f555e3
COPY --from=build /out/storefront-api /storefront-api
USER 65532:65532
EXPOSE 8080
ENTRYPOINT ["/storefront-api"]"""
scene("Tool 1: Docker & distroless", "Tool 1 · Docker + distroless", "The thing we ship: a tiny, non-root image",
      code("app/Dockerfile (excerpt)", DOCKERFILE, "docker", 21) + notes([
          (0, "Pinned by digest", "the base image cannot change under you"),
          (1, "Tests inside the build", "a failing test means no image"),
          (1, "Reproducible binary", "static, -trimpath, no build id"),
          (2, "Distroless + non-root", "no shell, no package manager, uid 65532"),
          (3, "3.7 MB, 0 findings", "less to exploit, scan gate stays green"),
      ]), [
    S("Let us go through every tool, starting with what we ship: a small Go service called storefront API. "
      "The Dockerfile is a two stage build. Notice that both base images are pinned by digest, not only by tag.", hl=(1, 2),
      tts="Let us go through every tool, starting with what we ship: a small Go service called storefront A P I. "
          "The Dockerfile is a two stage build. Notice that both base images are pinned by digest, not only by tag."),
    S("The unit tests run inside the build, so a failing test means no image. The binary is static, built with trim path and an empty build ID, so builds are reproducible.",
      hl=(8, 12), tts="The unit tests run inside the build, so a failing test means no image. The binary is static, built with trim path and an empty build I D, so builds are reproducible."),
    S("The final image is distroless: no shell, no package manager, and it runs as user 65532, never as root.", hl=(14, 18),
      tts="The final image is distroless: no shell, no package manager, and it runs as user 6 5 5 3 2, never as root."),
    S("The whole image is only 3.7 megabytes. Why does this matter for supply chain security? Fewer components mean fewer vulnerabilities, "
      "which keeps the scan gate green, and leaves an attacker almost nothing to work with.",
      tts="The whole image is only 3 point 7 megabytes. Why does this matter for supply chain security? Fewer components mean fewer vulnerabilities, "
          "which keeps the scan gate green, and leaves an attacker almost nothing to work with."),
], layout="code")

# ---------------------------------------------------------------- 6. GitHub Actions
RELEASE_TOP = """name: release
on:
  push:
    branches: [main]
permissions: {}            # nothing, unless a job asks

jobs:
  build:
    runs-on: ubuntu-24.04
    permissions:
      contents: read
      packages: write      # push image + signatures to GHCR
      id-token: write      # GitHub OIDC token -> keyless signing
    steps: [...]            # build, scan, push, SBOM, sign, verify

  e2e:                      # attack test against the new digest
    needs: build
    uses: ./.github/workflows/e2e.yaml

  promote:                  # commit the digest to deploy/prod
    needs: [build, e2e]"""
scene("Tool 2: GitHub Actions", "Tool 2 · GitHub Actions", "The release workflow is the trust anchor",
      code(".github/workflows/release.yaml (excerpt)", RELEASE_TOP, "yaml", 22) + notes([
          (0, "Trust anchor", "prod trusts only release.yaml on main"),
          (1, "permissions: {}", "deny by default"),
          (2, "Three grants", "read code · push packages · OIDC token"),
          (3, "id-token: write", "proves \"I am release.yaml on main\""),
          (4, "Ordered jobs", "build → attack test → promote"),
      ]), [
    S("Next, GitHub Actions. This is the release workflow. And here is the most important idea of the whole project: "
      "this workflow file is the trust anchor. Production trusts exactly one thing: signatures made by this file, on the main branch.", hl=(1, 4)),
    S("At the top, permissions is empty. No job gets any access unless it explicitly asks for it.", hl=(5, 5)),
    S("The build job asks for exactly three things: read the code, write packages so it can push the image, and an ID token.", hl=(10, 13),
      tts="The build job asks for exactly three things: read the code, write packages so it can push the image, and an I D token."),
    S("That ID token is what makes keyless signing possible. GitHub issues a short lived token that says: "
      "I am the release workflow, of this repository, running on the main branch.", hl=(13, 13),
      tts="That I D token is what makes keyless signing possible. GitHub issues a short lived token that says: "
          "I am the release workflow, of this repository, running on the main branch."),
    S("Then the jobs run in order: build and sign, then the attack test, then promote. Promote needs both earlier jobs to succeed.", hl=(16, 21)),
], layout="code")

# ---------------------------------------------------------------- 7. Pipeline hardening
scene(None, "Tool 2 · GitHub Actions", "Hardening the pipeline itself", grid([
    card(1, "📌", "Actions pinned by commit SHA", "actions/checkout@3d3c42e5… # v7.0.1 — a script fails CI on any unpinned action"),
    card(2, "💉", "No ${{ }} inside run:", "values go through env variables: closes template injection"),
    card(3, "🔐", "persist-credentials: false", "the checkout token is not left on disk"),
    card(3, "✅", "Tools by checksum", "cosign, Syft, Trivy downloaded and verified, fewer third-party actions"),
    card(4, "🧹", "zizmor + actionlint", "workflow security and syntax checks on every push"),
    card(4, "👥", "CODEOWNERS + Dependabot", "reviewed changes, pins kept up to date"),
], cols=2), [
    S("Because the pipeline is the trust anchor, the pipeline itself is hardened. This is exactly where the 2025 tag attack would have failed."),
    S("Every action is pinned to a full commit SHA, not to a tag. A tag can be moved, a commit SHA cannot. "
      "A small script in CI fails the build if anyone adds an unpinned action.",
      tts="Every action is pinned to a full commit shah, not to a tag. A tag can be moved, a commit shah cannot. "
          "A small script in C I fails the build if anyone adds an unpinned action."),
    S("No expressions are placed directly inside run blocks. Values are passed through environment variables, "
      "which closes the template injection hole that many workflow attacks use."),
    S("Checkout does not leave its token on disk. And tools like cosign, Syft and Trivy are downloaded with a checksum check, "
      "instead of adding more third party actions."),
    S("On every push, zizmor and actionlint scan the workflows for security mistakes. "
      "And CODEOWNERS plus Dependabot make sure changes are reviewed and pins stay up to date.",
      tts="On every push, zizmor and action lint scan the workflows for security mistakes. "
          "And code owners plus Dependabot make sure changes are reviewed and pins stay up to date."),
])

# ---------------------------------------------------------------- 8. Trivy
TRIVY = """- name: Vulnerability gate (no fixable CRITICAL or HIGH)
  run: |
    trivy image --quiet --exit-code 1 \\
      --severity CRITICAL,HIGH --ignore-unfixed \\
      "${IMAGE}:sha-${GITHUB_SHA::12}"

- name: Push by digest
  run: docker push ...       # -> outputs the sha256 digest

- name: SBOM, vulnerability report and provenance
  run: |
    syft scan "registry:${IMAGE}@${DIGEST}" \\
      -o cyclonedx-json=sbom.cdx.json
    trivy image --format cosign-vuln -o vuln.json \\
      "${IMAGE}@${DIGEST}"
    scripts/ci/provenance.sh "${IMAGE}@${DIGEST}" > provenance.json"""
scene("Tool 3: Trivy", "Tool 3 · Trivy", "Scan twice: a gate, then signed evidence",
      code(".github/workflows/release.yaml (excerpt)", TRIVY, "yaml", 22) + notes([
          (0, "Gate", "exit code 1 on fixable CRITICAL/HIGH → nothing is pushed"),
          (1, "Evidence", "cosign-vuln report, signed later"),
          (2, "Why both", "fast feedback + proof that travels to the cluster"),
      ]), [
    S("Tool number three is Trivy, a vulnerability scanner. It runs twice in the pipeline. First as a gate. "
      "If the image has any fixable critical or high vulnerability, exit code one stops the release, and nothing is pushed.", hl=(1, 5)),
    S("Second, after the push, Trivy writes its report in the cosign vuln format. That report gets signed, "
      "so the cluster can read a scan result that nobody could have faked.", hl=(14, 15)),
    S("Why both? The gate gives developers fast feedback. The signed report is evidence that travels with the image, all the way to the cluster."),
], layout="code")

# ---------------------------------------------------------------- 9. Syft
scene("Tool 4: Syft (SBOM)", "Tool 4 · Syft", "An ingredient list for every image",
      code(".github/workflows/release.yaml (excerpt)", TRIVY, "yaml", 22) + notes([
          (0, "Reads the pushed image", "by digest, straight from the registry"),
          (0, "CycloneDX JSON", "a standard SBOM format"),
          (1, "Are we affected?", "the next big CVE becomes a search"),
          (2, "Required at the door", "signed, attached, and checked by Kyverno"),
      ]), [
    S("Tool four is Syft, which creates the software bill of materials. It reads the pushed image, by digest, "
      "and lists every component inside, in the CycloneDX format.", hl=(12, 13),
      tts="Tool four is Sift, which creates the software bill of materials. It reads the pushed image, by digest, "
          "and lists every component inside, in the Cyclone D X format."),
    S("Why do we need it? When the next big vulnerability is announced, the question is always: are we affected? "
      "With an SBOM for every image, the answer is a search, not a week of investigation.", hl=(12, 13)),
    S("Regulations like the EU Cyber Resilience Act also ask for SBOMs. Here the SBOM is signed and attached to the image, "
      "and Kyverno refuses any image without one.",
      tts="Regulations like the E U Cyber Resilience Act also ask for S-boms. Here the S-bom is signed and attached to the image, "
          "and Kai-verno refuses any image without one."),
], layout="code")

# ---------------------------------------------------------------- 10. SLSA provenance
PROV = """jq -n --arg repo "$repo_url" --arg ref "$GITHUB_REF" \\
      --arg path "$workflow_path" --arg sha "$GITHUB_SHA" ... '{
  buildDefinition: {
    buildType: ".../buildtypes/docker-build/v1",
    externalParameters: {
      workflow: {repository: $repo, ref: $ref, path: $path}
    },
    resolvedDependencies: [
      {uri: ("git+" + $repo + "@" + $ref),
       digest: {gitCommit: $sha}}
    ]
  },
  runDetails: {
    builder: {id: $builder},
    metadata: {invocationId: $run,
               startedOn: $started, finishedOn: $finished}
  }
}'"""
scene("Tool 5: SLSA provenance", "Tool 5 · SLSA provenance", "Where and how was this image built?",
      code("scripts/ci/provenance.sh (excerpt)", PROV, "bash", 22) + notes([
          (0, "SLSA v1 format", "a standard way to describe a build"),
          (1, "Repository + branch + workflow", "Kyverno checks repo == ours, ref == main"),
          (2, "Exact commit + run link", "trace a pod back to a line of code"),
          (3, "Signed by cosign", "nobody else can produce a valid one"),
      ]), [
    S("Tool five is provenance, in the SLSA version one format. SLSA, pronounced salsa, is a framework that describes how software was built.",
      tts="Tool five is provenance, in the S L S A version one format. S L S A, pronounced salsa, is a framework that describes how software was built.", hl=(3, 4)),
    S("Our provenance records the repository, the branch, and the workflow file that ran the build. "
      "Later, Kyverno checks that the repository is ours, and that the branch is main.", hl=(5, 7)),
    S("It also records the exact git commit, and a link to the workflow run, so anyone can trace a running pod back to the line of code it came from.", hl=(8, 16)),
    S("On its own, this is just a JSON file. What makes it trustworthy is the next tool: it is signed by the release workflow, so nobody else can produce a valid one.",
      tts="On its own, this is just a jason file. What makes it trustworthy is the next tool: it is signed by the release workflow, so nobody else can produce a valid one."),
], layout="code")

# ---------------------------------------------------------------- 11. Sigstore cosign
SIGN = """legacy=(--new-bundle-format=false --use-signing-config=false --yes)
cosign sign   "${legacy[@]}" "${IMAGE}@${DIGEST}"
cosign attest "${legacy[@]}" --type slsaprovenance1 --predicate provenance.json ...
cosign attest "${legacy[@]}" --type vuln      --predicate vuln.json ...
cosign attest "${legacy[@]}" --type cyclonedx --predicate sbom.cdx.json ..."""
scene("Tool 6: Sigstore cosign", "Tool 6 · Sigstore cosign", "Keyless signing: no key to steal", svg(
    box(0, 0, 0, 520, 150, "🗝️", "Classic signing", ["a private key to store, rotate, protect…", "a stolen key signs anything"], "bad", "#2a1520")
    + box(1, 0, 190, 420, 170, "⚙️", "release.yaml job", ["has a GitHub OIDC token:", "\"repo X, release.yaml, main\""], "blue", "#16306a")
    + arrow(1, 425, 275, 555, 275, label="token")
    + box(2, 560, 190, 520, 170, "🏛️", "Fulcio (certificate authority)", ["10-minute certificate with", "the workflow identity inside"], "violet")
    + arrow(3, 1085, 275, 1195, 275, label="sign digest")
    + box(3, 1200, 190, 500, 170, "📦", "GHCR", [".sig + 3 .att next to the image"], "blue")
    + arrow(3, 820, 365, 820, 420)
    + box(3, 560, 425, 520, 120, "📒", "Rekor transparency log", ["public, append-only: anyone can audit"], "violet"),
    h=560) + f'<div class="st" data-s="4" style="margin-top:10px">{code("release.yaml: sign and attest", SIGN, "bash", 21)}</div>', [
    S("Now the heart of the project: Sigstore, and its command line tool, cosign. Classic signing needs a private key. "
      "Someone has to store it, protect it and rotate it. And a stolen key can sign anything.",
      tts="Now the heart of the project: Sigstore, and its command line tool, co-sign. Classic signing needs a private key. "
          "Someone has to store it, protect it and rotate it. And a stolen key can sign anything."),
    S("Keyless signing removes the key. The workflow shows its GitHub ID token to Fulcio, Sigstore's certificate authority.",
      tts="Keyless signing removes the key. The workflow shows its GitHub I D token to Fool-see-oh, Sigstore's certificate authority."),
    S("Fulcio issues a certificate that is valid for only ten minutes. Inside the certificate is the workflow identity: "
      "this repository, release dot yaml, on the main branch.",
      tts="Fool-see-oh issues a certificate that is valid for only ten minutes. Inside the certificate is the workflow identity: "
          "this repository, release dot yammel, on the main branch."),
    S("cosign signs the image digest with that certificate, stores the signature next to the image, and records it in Rekor, a public transparency log. "
      "Anyone can audit that log, and nobody can quietly remove an entry.",
      tts="Co-sign signs the image digest with that certificate, stores the signature next to the image, and records it in Recor, a public transparency log. "
          "Anyone can audit that log, and nobody can quietly remove an entry."),
    S("In the workflow, that is four commands: sign the image, then attest the provenance, the vulnerability report, and the SBOM. "
      "One detail cost me real debugging time: cosign version three writes a new bundle format by default, and Kyverno 1.19 did not find those signatures in my tests. "
      "So the pipeline uses the classic format, with new bundle format set to false.",
      tts="In the workflow, that is four commands: sign the image, then attest the provenance, the vulnerability report, and the S-bom. "
          "One detail cost me real debugging time: co-sign version three writes a new bundle format by default, and Kai-verno 1 point 19 did not find those signatures in my tests. "
          "So the pipeline uses the classic format, with new bundle format set to false.", hl=(1, 5)),
])

# ---------------------------------------------------------------- 12. GHCR & digests
scene("Tool 7: GHCR & digests", "Tool 7 · GitHub Container Registry", "Tags move. Digests don't.", svg(
    box(0, 0, 20, 820, 300, "🏷️", "Tag: storefront-api:v1", ["just a label", "anyone with write access can point it", "at different content tomorrow"], "bad", "#2a1520")
    + box(1, 880, 20, 840, 300, "#️⃣", "Digest: @sha256:38b5a66e…", ["the hash of the image content", "change one byte → a new digest", "signatures, git and pods all use it"], "ok", "#0f2a22")
    + box(2, 300, 400, 1120, 240, "📦", "ghcr.io/sufyanahmadkamboh/storefront-api", ["@sha256:38b5…  image", "sha256-38b5….sig  signature        sha256-38b5….att  3 attestations",
                                                                                   "the proof is stored next to the image and travels with it"], "blue", "#16306a")
), [
    S("Tool seven is the registry: the GitHub container registry. The important concept here is tags versus digests. "
      "A tag, like version one, is just a label. Anyone with write access can point it at different content."),
    S("A digest is the SHA 256 hash of the image content. If one byte changes, the digest changes. "
      "So signatures are made on digests, git stores digests, and pods run digests.",
      tts="A digest is the shah 256 hash of the image content. If one byte changes, the digest changes. "
          "So signatures are made on digests, git stores digests, and pods run digests."),
    S("The signature and the three attestations are stored right next to the image in the same registry, so the proof travels wherever the image goes."),
])

# ---------------------------------------------------------------- 13. Kyverno intro
scene("Tool 8: Kyverno", "Tool 8 · Kyverno", "Admission control: the guard at the door", svg(
    box(0, 0, 40, 330, 260, "👤", "Who asks?", ["kubectl", "a CI job", "Argo CD"], "blue")
    + arrow(0, 335, 170, 435, 170)
    + box(0, 440, 40, 360, 260, "☸️", "API server", ["receives the pod", "before storing it…"], "blue", "#16306a")
    + arrow(1, 805, 170, 905, 170, label="admission")
    + box(1, 910, 40, 380, 260, "🛂", "Kyverno webhooks", ["mutating: rewrite tag", "→ verified digest", "validating: allow / deny"], "amber", "#2b2410")
    + arrow(2, 1295, 120, 1395, 120, "ok")
    + box(2, 1400, 40, 320, 120, "✅", "Pod runs", [], "ok", "#0f2a22")
    + arrow(2, 1295, 230, 1395, 230, "bad")
    + box(2, 1400, 180, 320, 120, "⛔", "Never created", [], "bad", "#2a1520")
    + box(3, 200, 400, 1320, 220, "🧩", "Kyverno 1.19 policy types (CEL)", ["ImageValidatingPolicy → signatures and attestations",
                                                                          "ValidatingPolicy → registry, digests, pod safety",
                                                                          "(ClusterPolicy is deprecated)"], "violet")
), [
    S("Tool eight is the guard at the door: Kyverno. Every request to create or change a pod goes to the Kubernetes API server.",
      tts="Tool eight is the guard at the door: Kai-verno. Every request to create or change a pod goes to the Kubernetes A P I server."),
    S("Before the object is stored, the API server asks admission webhooks for their opinion. Kyverno is one of them.",
      tts="Before the object is stored, the A P I server asks admission webhooks for their opinion. Kai-verno is one of them."),
    S("If Kyverno says no, the pod is never created. It does not matter whether the request came from a person with kubectl, from a CI job, or from Argo CD.",
      tts="If Kai-verno says no, the pod is never created. It does not matter whether the request came from a person with kube control, from a C I job, or from Argo C D."),
    S("This project uses the new Kyverno 1.19 policy types, written in CEL, the same expression language Kubernetes itself uses. The older ClusterPolicy type is deprecated.",
      tts="This project uses the new Kai-verno 1 point 19 policy types, written in cel, the same expression language Kubernetes itself uses. The older cluster policy type is deprecated."),
])

# ---------------------------------------------------------------- 14. verify-images policy
VERIFY = """kind: ImageValidatingPolicy
metadata: {name: verify-release-images}
spec:
  validationActions: [Deny]
  matchConstraints:
    namespaceSelector:
      matchLabels: {supply-chain.sufyan.dev/enforce: "true"}
  matchImageReferences:
    - glob: "ghcr.io/sufyanahmadkamboh/storefront-api*"
  attestors:
    - name: release-workflow
      cosign:
        keyless:
          identities:
            - issuer: https://token.actions.githubusercontent.com
              subject: https://github.com/…/.github/workflows/release.yaml@refs/heads/main
        ctlog: {url: https://rekor.sigstore.dev}
  attestations:
    - {name: provenance, intoto: {type: https://slsa.dev/provenance/v1}}
    - {name: vulnerabilities, intoto: {type: https://cosign.sigstore.dev/attestation/vuln/v1}}
    - {name: sbom, intoto: {type: https://cyclonedx.org/bom}}
  validationConfigurations: {mutateDigest: true, verifyDigest: true, required: true}
  validations:   # signature · provenance repo + main · scan has no CRITICAL/HIGH · SBOM
    - expression: >-
        images.containers.map(image, verifyImageSignatures(image,
          [attestors["release-workflow"]])).all(n, n > 0)"""
scene(None, "Tool 8 · Kyverno", "Policy: verify-release-images",
      code("policies/base/verify-images.yaml (excerpt)", VERIFY, "yaml", 17) + notes([
          (0, "Opt-in per namespace", "label enforce=true"),
          (1, "Who may sign", "GitHub OIDC · release.yaml · main · logged in Rekor"),
          (2, "Required documents", "provenance · scan · SBOM"),
          (3, "mutateDigest", "run exactly what was verified"),
          (4, "Readable refusals", "every rule has a message"),
      ]), [
    S("Here is the main policy: verify release images. It only applies to namespaces with the label enforce equals true. So you decide, namespace by namespace.", hl=(5, 7)),
    S("The attestor is the most important part. It says: the signature must come from a Sigstore certificate issued by GitHub, for the subject release dot yaml "
      "on the main branch of this repository. And it must be recorded in the Rekor log.", hl=(10, 17),
      tts="The attestor is the most important part. It says: the signature must come from a Sigstore certificate issued by GitHub, for the subject release dot yammel "
          "on the main branch of this repository. And it must be recorded in the Recor log."),
    S("Then we declare the three documents we expect: the provenance, the vulnerability report, and the SBOM.", hl=(18, 21),
      tts="Then we declare the three documents we expect: the provenance, the vulnerability report, and the S-bom."),
    S("Mutate digest rewrites the pod's image to the exact digest that was verified. So nobody can move a tag between the check and the start of the container.", hl=(22, 22)),
    S("Finally, the validations. The signature must verify. The provenance must name this repository and main. The signed scan must have no critical or high findings. "
      "And the signed SBOM must exist. Every rule has a clear message, so a refused developer knows exactly why.", hl=(23, 26),
      tts="Finally, the validations. The signature must verify. The provenance must name this repository and main. The signed scan must have no critical or high findings. "
          "And the signed S-bom must exist. Every rule has a clear message, so a refused developer knows exactly why."),
], layout="code")

# ---------------------------------------------------------------- 15. other policies + PSA
NS = """apiVersion: v1
kind: Namespace
metadata:
  name: prod
  labels:
    # our Kyverno policies, in Deny mode
    supply-chain.sufyan.dev/enforce: "true"
    # Kubernetes built-in Pod Security Admission
    pod-security.kubernetes.io/enforce: restricted"""
scene(None, "Tool 8 · Kyverno + Pod Security", "Two more policies, two locks on the door",
      grid([card(0, "📍", "allowed-images", "only ghcr.io/sufyanahmadkamboh/storefront-api — Docker Hub refused in ~0.5 s"),
            card(1, "#️⃣", "digests in git", "Deployments, StatefulSets… must use image@sha256:…, never a tag"),
            card(2, "🧯", "restricted-pods", "non-root, no privilege escalation, read-only root, drop ALL, CPU + memory limits"),
            ], cols=3, gap=20)
      + f'<div class="st" data-s="3" style="margin-top:26px;width:1100px">{code("deploy/prod/namespace.yaml", NS, "yaml", 22)}</div>', [
    S("Two more policies close the simple gaps. Allowed images says that pods in production may only use images from our own repository. "
      "A Docker Hub image is refused in about half a second, before any signature is even checked."),
    S("It also requires workloads stored in git, like Deployments, to reference images by digest, never by a movable tag."),
    S("Restricted pods covers the case where a trusted image is started in a dangerous way: as root, privileged, with host access, or without resource limits."),
    S("The production namespace switches all of this on with two labels. One for our Kyverno policies, and one for the Pod Security admission that is built into Kubernetes, "
      "at the restricted level. Two independent locks on the same door.",
      tts="The production namespace switches all of this on with two labels. One for our Kai-verno policies, and one for the Pod Security admission that is built into Kubernetes, "
          "at the restricted level. Two independent locks on the same door."),
])

# ---------------------------------------------------------------- 16. Audit mode
AUDIT = """# Sandbox: the same rules in AUDIT mode
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../base
nameSuffix: -audit
patches:
  - target:
      group: policies.kyverno.io
    patch: |-
      - op: replace
        path: /spec/validationActions
        value: [Audit]
      - op: replace
        path: /spec/matchConstraints/namespaceSelector/matchLabels
        value:
          supply-chain.sufyan.dev/audit: "true\""""
scene("Rollout: audit first", "Kustomize · audit mode", "Roll out safely: audit, fix, then enforce",
      code("policies/sandbox/kustomization.yaml", AUDIT, "yaml", 22) + notes([
          (0, "Day one problem", "strict rules can break every team"),
          (1, "Same policies, -audit", "Deny → Audit, for label audit=true"),
          (2, "Nothing blocked", "violations in PolicyReports + Prometheus"),
          (3, "Measured", "violations reported 18 s later"),
      ]), [
    S("How do you introduce rules like these without breaking every team on day one? With audit mode."),
    S("A Kustomize overlay creates a copy of every policy with the suffix audit, and patches the action from Deny to Audit, for namespaces with the label audit.", hl=(6, 17),
      tts="A customize overlay creates a copy of every policy with the suffix audit, and patches the action from Deny to Audit, for namespaces with the label audit."),
    S("In audit mode nothing is blocked. Violations show up in policy reports and in Prometheus. Teams fix what the reports find, and then you switch the namespace label from audit to enforce."),
    S("In the test, an unsigned image runs fine in the sandbox namespace, and the policy reports list its violations eighteen seconds later."),
], layout="code")

# ---------------------------------------------------------------- 17. Argo CD + Kustomize
APP = """# deploy/prod/kustomization.yaml
namespace: prod
resources: [namespace.yaml, ../base]
images:
  - name: ghcr.io/sufyanahmadkamboh/storefront-api
    digest: sha256:38b5a66e735e9d2c2e470b8d5b8c83dc…   # set by promote

# platform/argocd/application.yaml
kind: Application
spec:
  source:
    repoURL: https://github.com/sufyanahmadkamboh/sufyan-devops-secure-supply-chain.git
    targetRevision: main
    path: deploy/prod
  syncPolicy:
    automated: {prune: true, selfHeal: true}"""
scene("Tool 9: Argo CD & Kustomize", "Tool 9 · Argo CD + Kustomize", "GitOps: git decides what should run",
      code("deploy/prod + Argo CD Application (excerpts)", APP, "yaml", 18) + notes([
          (0, "Single source of truth", "deploy/prod on main"),
          (1, "Digest, not tag", "only the promote job changes it"),
          (2, "Automated sync", "prune + self-heal: drift is undone"),
          (3, "Not trusted for security", "a bad commit is still refused by Kyverno"),
      ]), [
    S("Tool nine is GitOps, with Argo CD and Kustomize. The production folder in git is the single source of truth for what should run.", hl=(1, 3),
      tts="Tool nine is git ops, with Argo C D and customize. The production folder in git is the single source of truth for what should run."),
    S("The production kustomization pins the image by digest. Only the release pipeline changes this line, and only after the attack test has passed.", hl=(4, 6),
      tts="The production customization pins the image by digest. Only the release pipeline changes this line, and only after the attack test has passed."),
    S("Argo CD watches that folder on main, with automated sync, prune and self heal. If someone changes the cluster by hand, Argo CD puts it back.", hl=(9, 16),
      tts="Argo C D watches that folder on main, with automated sync, prune and self heal. If someone changes the cluster by hand, Argo C D puts it back."),
    S("And here is a key design decision: Argo CD is not trusted with security. If an attacker manages to commit a bad digest, Argo CD will try to apply it, "
      "and Kyverno will refuse it. We test exactly that on every release.",
      tts="And here is a key design decision: Argo C D is not trusted with security. If an attacker manages to commit a bad digest, Argo C D will try to apply it, "
          "and Kai-verno will refuse it. We test exactly that on every release."),
], layout="code")

# ---------------------------------------------------------------- 18. Promote
PROMOTE = """promote:
  needs: [build, e2e]          # only after the attack test passed
  permissions:
    contents: write             # commit to deploy/prod, nothing else
  steps:
    - uses: actions/checkout@3d3c42e5…   # v7.0.1, pinned by SHA
    - name: Commit the verified digest
      run: |
        sed -i -E "s|(    digest: )sha256:[a-f0-9]{64}|\\1${DIGEST}|" \\
          deploy/prod/kustomization.yaml
        git commit -am "deploy: storefront-api ${DIGEST:7:12}"
        git push origin HEAD:main"""
scene(None, "Tool 9 · GitOps promotion", "A deployment is a git commit",
      code(".github/workflows/release.yaml: promote (excerpt)", PROMOTE, "yaml", 21) + notes([
          (0, "Gated", "needs build AND the attack test"),
          (1, "One line changes", "the digest in deploy/prod"),
          (2, "Rollback = git revert", "old digests stay signed and verifiable"),
      ]), [
    S("This is the promote job. It only runs when the build and the attack test both succeeded, and its only permission is to write to the repository.", hl=(1, 4)),
    S("It replaces the digest in the production kustomization with the new, verified digest, and commits it to main as a release bot.", hl=(7, 12),
      tts="It replaces the digest in the production customization with the new, verified digest, and commits it to main as a release bot."),
    S("That commit is the deployment. To roll back, you simply revert it. Argo CD then deploys the previous digest, which is still signed and still verifiable.",
      tts="That commit is the deployment. To roll back, you simply revert it. Argo C D then deploys the previous digest, which is still signed and still verifiable."),
], layout="code")

# ---------------------------------------------------------------- 19. Trivy Operator
scene("Tool 10: Trivy Operator", "Tool 10 · Trivy Operator", "New CVEs appear after you ship", svg(
    box(0, 0, 30, 520, 250, "📅", "Day 0: release", ["signed scan: 0 critical", "admitted ✅"], "ok", "#0f2a22")
    + arrow(0, 525, 155, 625, 155)
    + box(0, 630, 30, 520, 250, "📰", "Day 30: new CVE published", ["the signature is still valid", "the image is not safe anymore"], "bad", "#2a1520")
    + box(1, 1200, 30, 520, 250, "📡", "Trivy Operator", ["in the cluster, watches prod", "and sandbox, re-scans", "running images"], "amber", "#2b2410")
    + box(1, 300, 360, 520, 200, "📋", "VulnerabilityReport", ["one per running image"], "blue")
    + box(1, 900, 360, 520, 200, "📈", "Prometheus metrics", ["trivy_image_vulnerabilities"], "blue")
    + label(2, 860, 650, "test: nginx:1.21.0 in sandbox → 27 CRITICAL · 134 HIGH found after 90 s", 32, "amber", "middle", 900)
), [
    S("Signing proves where an image came from. It does not protect you from a vulnerability that is published next month. That is the job of tool ten: Trivy Operator."),
    S("It runs inside the cluster, watches the running workloads in prod and in sandbox, and re-scans their images. The results become vulnerability reports, and Prometheus metrics."),
    S("In the test, an old nginx image is started in the sandbox. Trivy Operator found twenty seven critical vulnerabilities in it, ninety seconds later.",
      tts="In the test, an old engine x image is started in the sandbox. Trivy Operator found twenty seven critical vulnerabilities in it, ninety seconds later."),
])

# ---------------------------------------------------------------- 20. Prometheus alerts
RULES = """groups:
  - name: supply-chain
    rules:
      - alert: UntrustedWorkloadBlocked     # refused in prod (10 min)
        expr: >-
          sum by (resource_namespace, resource_kind) (
            (new refusal counters, after Prometheus is 10 min old)
            or increase(kyverno_admission_requests_total{
                 request_allowed="false", resource_namespace="prod"}[10m])
          ) > 0
      - alert: RunningImageHasCriticalVulnerabilities
        expr: sum by (namespace, image_repository, image_tag, image_digest) (
                trivy_image_vulnerabilities{severity="Critical"}) > 0
        for: 5m
      - alert: AdmissionControllerDown
        expr: absent(up{job="kyverno-admission"} == 1)
        for: 5m"""
scene("Tool 11: Prometheus & Grafana", "Tool 11 · Prometheus", "Three alerts that matter",
      code("platform/monitoring/rules.yaml (simplified)", RULES, "yaml", 20) + notes([
          (1, "Blocked in prod", "a healthy pipeline never triggers it"),
          (2, "Critical CVE running", "from Trivy Operator, for 5 minutes"),
          (3, "Kyverno down", "fail closed: no new pods can start"),
          (4, "Unit-tested", "promtool tests, 5 groups"),
      ]), [
    S("Tool eleven is Prometheus. It collects the metrics from Kyverno and from Trivy Operator, and three alert rules watch them."),
    S("Untrusted workload blocked fires when anything is refused in production. In a healthy pipeline that never happens, so even one refusal is worth a look.", hl=(4, 10)),
    S("Running image has critical vulnerabilities fires when Trivy Operator finds critical issues in a running image for five minutes.", hl=(11, 14)),
    S("And admission controller down fires when Kyverno itself disappears. Remember, Kyverno fails closed: when it is down, no new pods can start.", hl=(15, 17),
      tts="And admission controller down fires when Kai-verno itself disappears. Remember, Kai-verno fails closed: when it is down, no new pods can start."),
    S("All three rules have unit tests that run with promtool in CI. And those tests, together with a live demo, found real bugs.",
      tts="All three rules have unit tests that run with prom tool in C I. And those tests, together with a live demo, found real bugs."),
], layout="code")

# ---------------------------------------------------------------- 21. Lessons from the alerts
scene(None, "Lessons learned", "Test your alerts against real attacks", grid([
    card(0, "🐞", "Bug 1: the wrong webhook phase", "the first rule counted only Kyverno's validating phase", "bad"),
    card(1, "🔁", "Signature failures are mutating", "the image policy rewrites tags → refusals happen in the mutating phase; demo: 10 counted, 19 happened", "bad"),
    card(2, "📉", "Bug 2: increase() misses the start", "Kyverno creates a counter that already starts at 3 → no visible increase", "bad"),
    card(3, "✅", "Fixed + tested", "both phases counted, new counters counted, promtool tests for both cases", "ok"),
], cols=2), [
    S("Here is an honest lesson from building this. My first version of the alert only counted refusals from Kyverno's validating webhook.",
      tts="Here is an honest lesson from building this. My first version of the alert only counted refusals from Kai-verno's validating webhook."),
    S("But the image policy also rewrites images to their digest, so signature failures are refused in the mutating phase. "
      "The alert missed exactly the most important refusals: unsigned and imposter images. A local demo showed ten refusals where nineteen had happened."),
    S("The second bug: Prometheus' increase function cannot see the very first refusals, because Kyverno creates the counter when it already has a value, for example three.",
      tts="The second bug: Prometheus' increase function cannot see the very first refusals, because Kai-verno creates the counter when it already has a value, for example three."),
    S("Both are fixed, and both cases now have unit tests. The lesson is simple: test your alerts against real attacks, not just against your expectations."),
])

# ---------------------------------------------------------------- 22. Grafana
scene(None, "Tool 11 · Grafana", "One dashboard: what runs, and why",
      '<img class="shot st" data-s="0" src="../../docs/images/grafana-dashboard.png" alt="Grafana dashboard">', [
    S("Grafana shows it all on one dashboard. This is the local lab after a demo. At the top: what was blocked in production, the signature checks, "
      "running images with critical vulnerabilities, and the firing alerts."),
    S("Below, refusals over time, image verification results, vulnerabilities per image, and the health of the admission controller. "
      "The dashboard is provisioned from a JSON file in git, like everything else in this project.",
      tts="Below, refusals over time, image verification results, vulnerabilities per image, and the health of the admission controller. "
          "The dashboard is provisioned from a jason file in git, like everything else in this project."),
])

# ---------------------------------------------------------------- 23. kind + e2e
scene("Tool 12: the attack test", "Tool 12 · kind + the e2e attack test", "Every release attacks itself first", checklist([
    (1, "1", "Platform", "fresh kind cluster: Kyverno, policies, Argo CD, Trivy Operator, Prometheus, Grafana (156 s)"),
    (2, "2", "Real deployment", "the new signed digest goes through Argo CD (2/2 pods after 18 s)"),
    (3, "3", "Attacks at the door", "foreign · unsigned · tampered · imposter-signed · privileged; control admitted"),
    (4, "4", "Attack through git", "malicious commit to deploy/prod → refused, prod keeps serving, revert"),
    (4, "5", "Audit + live scanning", "sandbox audit mode, PolicyReports, Trivy Operator, CVE alert"),
    (4, "6", "Monitoring", "alerts fired as expected, admission controller healthy"),
    (5, "✋", "Any surprise → job fails", "promote never runs: a weaker release can't reach production"),
]), [
    S("Tool twelve is kind, Kubernetes in Docker. It powers the part that makes this project different: an end to end attack test that runs on every release, "
      "on a brand new cluster inside GitHub Actions."),
    S("Section one builds the whole platform: Kyverno, the policies, Argo CD, Trivy Operator, Prometheus and Grafana. That takes about two and a half minutes.",
      tts="Section one builds the whole platform: Kai-verno, the policies, Argo C D, Trivy Operator, Prometheus and Grafana. That takes about two and a half minutes."),
    S("Section two deploys the new signed release the real way, through Argo CD.", tts="Section two deploys the new signed release the real way, through Argo C D."),
    S("Section three attacks the cluster door directly. It pushes attacker images into our real registry, which simulates a stolen token."),
    S("Section four attacks through git, with a malicious commit to the production folder. Section five checks audit mode and live scanning, and section six checks the alerts."),
    S("If anything is not refused, the job fails, and the promote job never runs. A release that weakens the defences can never reach production."),
])

# ---------------------------------------------------------------- 24. Imposter
scene(None, "The most interesting attack", "Signed is not the same as trusted", svg(
    box(0, 0, 20, 540, 250, "🦈", "Imposter workflow: e2e.yaml", ["a second workflow in the SAME", "repository (the Megalodon idea)"], "bad", "#2a1520")
    + arrow(1, 545, 145, 640, 145, "bad")
    + box(1, 645, 20, 520, 250, "🔏", "A VALID Sigstore signature", ["+ forged provenance", "+ a clean-looking scan", "verified by cosign ✓"], "amber", "#2b2410")
    + arrow(2, 1170, 145, 1265, 145, "bad")
    + box(2, 1270, 20, 450, 250, "⛔", "Refused in 1,970 ms", ["by verify-release-images"], "ok", "#0f2a22")
    + box(2, 160, 360, 1400, 170, "🔎", "Why? Kyverno checks WHO signed", ["certificate subject: …/.github/workflows/e2e.yaml@refs/heads/main",
                                                                      "required subject:     …/.github/workflows/release.yaml@refs/heads/main"], "blue", "#16306a")
), [
    S("The most interesting attack is the imposter. It copies the Megalodon idea: a second workflow file in the same repository, called e2e dot yaml.",
      tts="The most interesting attack is the imposter. It copies the Megalodon idea: a second workflow file in the same repository, called e 2 e dot yammel."),
    S("That workflow takes a tampered image and signs it with a completely valid Sigstore signature. It even attaches forged provenance and a clean looking scan. "
      "The test first verifies that this signature really is valid."),
    S("Kyverno still refuses it, in about two seconds. Why? The certificate says e2e dot yaml, not release dot yaml. Signed is not the same as trusted. The policy checks who signed.",
      tts="Kai-verno still refuses it, in about two seconds. Why? The certificate says e 2 e dot yammel, not release dot yammel. Signed is not the same as trusted. The policy checks who signed."),
])

# ---------------------------------------------------------------- 25. Results
scene("Measured results", "Measured on GitHub Actions · run 37119604685", "7 attacks: 6 refused, 1 caught", grid([
    tile(1, "🌍", "Image from another registry", "484 ms", "ok", "allowed-images"),
    tile(2, "🔑", "Unsigned image, stolen token", "2,058 ms", "ok", "verify-release-images"),
    tile(2, "🧬", "Tampered copy of our image", "1,968 ms", "ok", "verify-release-images"),
    tile(2, "🦈", "Valid signature, wrong workflow", "1,970 ms", "ok", "verify-release-images"),
    tile(3, "👑", "Our image, privileged", "363 ms", "ok", "Pod Security restricted"),
    tile(4, "🐙", "Malicious commit to git", "6 s", "ok", "after the push · prod kept serving"),
    tile(5, "🕳️", "Old image with known CVEs", "27 CRITICAL", "amber", "alert fired"),
    tile(5, "✅", "The real release", "admitted", "ok", "every time"),
], cols=4, gap=20), [
    S("So here are the measured results, from a real GitHub Actions run that is linked in the description. The times show how long the cluster took to say no."),
    S("An image from another registry: refused in 484 milliseconds.", tts="An image from another registry: refused in 484 milliseconds."),
    S("An unsigned image pushed with a stolen token: refused in about two seconds. A tampered copy of our image: two seconds. And the imposter, with a valid signature: also two seconds."),
    S("Our own image started as a privileged container: refused in 363 milliseconds, by Pod Security."),
    S("The malicious git commit: Argo CD applied it, and the cluster refused it six seconds after the push. Production kept serving the whole time.",
      tts="The malicious git commit: Argo C D applied it, and the cluster refused it six seconds after the push. Production kept serving the whole time."),
    S("And the old nginx image with known vulnerabilities was found, and its alert fired. Meanwhile, the real release was admitted every single time.",
      tts="And the old engine x image with known vulnerabilities was found, and its alert fired. Meanwhile, the real release was admitted every single time."),
])

# ---------------------------------------------------------------- 26/27. Production rollout
# ---------------------------------------------------------------- Hands-on lab (real output from a fresh clone)
scene("Hands-on: run it on your laptop", "Hands-on lab · what you need", "Run the whole platform on your laptop", checklist([
    (1, "🐳", "Docker Desktop (or Docker Engine)", "give it 4 CPUs and 8 GB of memory"),
    (2, "☸️", "kind + git", "kind creates the Kubernetes cluster inside Docker"),
    (2, "⌨️", "A Bash terminal", "macOS / Linux terminal, or Git Bash on Windows"),
    (3, "🌐", "An internet connection", "pulls images and checks signatures with Sigstore; no cloud account, no cost"),
]), [
    S("Now let us make this practical. You can run the whole platform on your own laptop, for free, and attack it yourself. "
      "I recorded every command and output in this part from a fresh clone of the repository, so you will see exactly what to expect."),
    S("You need Docker, with at least four CPUs and eight gigabytes of memory available."),
    S("You need kind, which creates a Kubernetes cluster inside Docker, and git. Any Bash terminal works: macOS, Linux, or Git Bash on Windows."),
    S("And an internet connection, because the cluster pulls the signed release from the registry and checks its signatures with Sigstore. "
      "There is no cloud account to create, and nothing costs money. Every other tool, like kubectl, Helm and cosign, runs inside a container that the scripts build for you.",
      tts="And an internet connection, because the cluster pulls the signed release from the registry and checks its signatures with Sigstore. "
          "There is no cloud account to create, and nothing costs money. Every other tool, like kube control, Helm and co-sign, runs inside a container that the scripts build for you."),
])

scene(None, "Hands-on lab · step 1", "Clone it and start the platform", terminal([
    (0, "$ git clone https://github.com/sufyanahmadkamboh/sufyan-devops-secure-supply-chain.git", "cmd"),
    (0, "$ cd sufyan-devops-secure-supply-chain", "cmd"),
    (0, "$ scripts/platform-up.sh", "cmd"),
    (1, "==> Building the toolbox image", "out"),
    (1, "==> Creating kind cluster supply-chain", "out"),
    (2, "==> Kyverno (chart 3.9.1)", "out"),
    (2, "==> Admission policies (prod: Deny, sandbox: Audit)", "out"),
    (2, "==> Namespaces", "out"),
    (2, "==> Argo CD v3.5.3", "out"),
    (2, "==> Trivy Operator (chart 0.36.0), scanning prod and sandbox", "out"),
    (2, "==> Prometheus + Grafana", "out"),
    (2, "==> Argo CD Application (follows: main)", "out"),
    (3, " ok Platform ready", "ok"),
    (3, "# 3 min 37 s on my laptop, from a fresh clone (including the toolbox build)", "dim"),
], "bash"), [
    S("Step one: clone the repository, go into the folder, and run the platform up script. That is the only setup command."),
    S("First it builds the toolbox image, with kubectl, Helm, cosign, crane and the Kyverno command line, all pinned and checksum verified. "
      "Then it creates a kind cluster with a control plane and a worker node.",
      tts="First it builds the toolbox image, with kube control, Helm, co-sign, crane and the Kai-verno command line, all pinned and checksum verified. "
          "Then it creates a kind cluster with a control plane and a worker node."),
    S("Next it installs Kyverno and the policies, labels the namespaces, installs Argo CD, Trivy Operator, Prometheus and Grafana, "
      "and finally points Argo CD at the production folder on the main branch."),
    S("From a fresh clone on my laptop, this took three minutes and thirty seven seconds. A minute later, Argo CD has deployed the signed release."),
])

scene(None, "Hands-on lab · step 2", "Look around: what runs where", terminal([
    (0, "$ scripts/try.sh status", "cmd"),
    (1, "==> Platform", "out"),
    (1, "argocd        argocd-server-665b8b6947-nv8k2                     Running", "out"),
    (1, "kyverno       kyverno-admission-controller-769b8f7647-h447v      Running", "out"),
    (1, "monitoring    grafana-7d46d56c7c-kqblg                           Running", "out"),
    (1, "trivy-system  trivy-operator-85bdc5d5fc-sgmpg                    Running", "out"),
    (1, "prod          storefront-api-7785589b67-cfj7w                    Running", "out"),
    (2, "==> Admission policies (prod: Deny, sandbox: Audit)", "out"),
    (2, "imagevalidatingpolicy.policies.kyverno.io/verify-release-images", "out"),
    (2, "validatingpolicy.policies.kyverno.io/allowed-images", "out"),
    (2, "validatingpolicy.policies.kyverno.io/restricted-pods            (+ 3 x -audit)", "out"),
    (3, "==> The release Argo CD deployed to prod", "out"),
    (3, "Synced / Healthy", "ok"),
    (3, "storefront-api-…-cfj7w  ghcr.io/sufyanahmadkamboh/storefront-api@sha256:cb9b332ce38c9efb…", "ok"),
], "bash · excerpt"), [
    S("Step two: look around. Every exercise is one command: scripts slash try dot S H, followed by the name of the exercise. Start with status.",
      tts="Step two: look around. Every exercise is one command: scripts slash try dot S H, followed by the name of the exercise. Start with status."),
    S("You see the platform: Argo CD, Kyverno, Grafana and Prometheus, Trivy Operator, and our storefront API running in the prod namespace.",
      tts="You see the platform: Argo C D, Kai-verno, Grafana and Prometheus, Trivy Operator, and our storefront A P I running in the prod namespace."),
    S("There are six policies: our three, plus an audit copy of each for the sandbox namespace."),
    S("And the release in prod is synced and healthy, and pinned to a digest. Argo CD deployed it from git, and Kyverno verified it on the way in.",
      tts="And the release in prod is synced and healthy, and pinned to a digest. Argo C D deployed it from git, and Kai-verno verified it on the way in."),
])

scene(None, "Hands-on lab · step 3", "Verify the signature yourself", terminal([
    (0, "$ scripts/try.sh verify", "cmd"),
    (0, "==> Is ghcr.io/sufyanahmadkamboh/storefront-api@sha256:cb9b332ce38c… signed by release.yaml on main?", "out"),
    (1, "The following checks were performed on each of these signatures:", "out"),
    (1, "  - The cosign claims were validated", "out"),
    (1, "  - Existence of the claims in the transparency log was verified offline", "out"),
    (1, "  - The code-signing certificate was verified using trusted certificate authority certificates", "out"),
    (2, "built from commit 2770967ea684b2ebf86c429430ed26921568a503 by release (push)", "ok"),
    (2, " ok signed slsaprovenance1 attestation", "ok"),
    (2, " ok signed vuln attestation", "ok"),
    (2, " ok signed cyclonedx attestation", "ok"),
    (3, "$ scripts/try.sh wrong-identity", "cmd"),
    (3, "==> Same image, but expecting a different workflow (ci.yaml) as the signer", "out"),
    (3, "FAILED as expected. The certificate was issued to:", "bad"),
    (3, "  https://github.com/sufyanahmadkamboh/sufyan-devops-secure-supply-chain/.github/workflows/release.yaml@refs/heads/main", "bad"),
], "bash"), [
    S("Step three: verify the release yourself, exactly the way the cluster does. Run try dot S H verify.", tts="Step three: verify the release yourself, exactly the way the cluster does. Run try dot S H verify."),
    S("cosign checks the signature, the certificate from Sigstore's certificate authority, and the entry in the public transparency log.",
      tts="Co-sign checks the signature, the certificate from Sigstore's certificate authority, and the entry in the public transparency log."),
    S("It tells you the exact commit and workflow that built the image, and that all three attestations are signed: provenance, the vulnerability scan, and the SBOM.",
      tts="It tells you the exact commit and workflow that built the image, and that all three attestations are signed: provenance, the vulnerability scan, and the S-bom."),
    S("Now run wrong identity. It does the same check, but expects a different workflow, ci dot yaml, as the signer. It fails, and shows you who really signed: release dot yaml on main. "
      "This one check is what stops an injected workflow.",
      tts="Now run wrong identity. It does the same check, but expects a different workflow, C I dot yammel, as the signer. It fails, and shows you who really signed: release dot yammel on main. "
          "This one check is what stops an injected workflow."),
])

scene(None, "Hands-on lab · step 4", "Be the attacker", terminal([
    (0, "$ scripts/try.sh trusted", "cmd"),
    (0, "ADMITTED pod/try-trusted created", "ok"),
    (1, "$ scripts/try.sh foreign", "cmd"),
    (1, "REFUSED denied the request: Policy allowed-images failed: only ghcr.io/sufyanahmadkamboh/storefront-api", "bad"),
    (1, "        images may run here, got: docker.io/library/nginx:1.29", "bad"),
    (2, "$ scripts/try.sh unsigned", "cmd"),
    (2, "==> Building your own image as ghcr.io/sufyanahmadkamboh/storefront-api:local and side-loading it onto the nodes", "out"),
    (2, "REFUSED denied the request: Policy verify-release-images error: failed to update digest: failed to resolve", "bad"),
    (2, "        digest for image ghcr.io/sufyanahmadkamboh/storefront-api:local …", "bad"),
    (3, "$ scripts/try.sh privileged", "cmd"),
    (3, "REFUSED violates PodSecurity \"restricted:latest\": privileged (container \"app\" must not set", "bad"),
    (3, "        securityContext.privileged=true), allowPrivilegeEscalation != false …", "bad"),
], "bash"), [
    S("Step four: be the attacker. First the control: try dot S H trusted starts the signed release as a pod in prod. It is admitted.",
      tts="Step four: be the attacker. First the control: try dot S H trusted starts the signed release as a pod in prod. It is admitted."),
    S("Now foreign: an nginx image from Docker Hub. Refused by allowed images, with a message that says exactly why.",
      tts="Now foreign: an engine x image from Docker Hub. Refused by allowed images, with a message that says exactly why."),
    S("Unsigned is a sneaky one. It builds your own image on your laptop, gives it our trusted name, and side loads it straight onto the cluster nodes, skipping the registry. "
      "Kyverno refuses it: it insists on finding the image and its signatures in the registry, and an image it cannot verify there never runs.",
      tts="Unsigned is a sneaky one. It builds your own image on your laptop, gives it our trusted name, and side loads it straight onto the cluster nodes, skipping the registry. "
          "Kai-verno refuses it: it insists on finding the image and its signatures in the registry, and an image it cannot verify there never runs."),
    S("And privileged starts our own, trusted image as a privileged container. Pod Security refuses it, before Kyverno even looks at the image.",
      tts="And privileged starts our own, trusted image as a privileged container. Pod Security refuses it, before Kai-verno even looks at the image."),
])

scene(None, "Hands-on lab · step 5", "Audit mode and the vulnerability scanner", terminal([
    (0, "$ scripts/try.sh sandbox", "cmd"),
    (0, "ADMITTED pod/try-sandbox created", "ok"),
    (0, "==> Waiting for the PolicyReport (audit mode reports instead of blocking)", "out"),
    (0, "would be refused in prod: allowed-images-audit", "warn"),
    (1, "$ scripts/try.sh scan", "cmd"),
    (1, "ADMITTED pod/try-scan created", "ok"),
    (1, "==> Waiting for Trivy Operator to scan it (a few minutes the first time)", "out"),
    (1, "library/nginx:1.21.0  CRITICAL 27  HIGH 134", "bad"),
    (2, "$ scripts/try.sh alerts", "cmd"),
    (2, "firing   UntrustedWorkloadBlocked                 Kyverno blocked 4 Pod request(s) in prod (10 min)", "bad"),
    (2, "pending  RunningImageHasCriticalVulnerabilities   sandbox: library/nginx has 6 CRITICAL vulnerabilities", "warn"),
], "bash"), [
    S("Step five: audit mode. try dot S H sandbox starts the same Docker Hub image in the sandbox namespace. This time it is admitted, "
      "and a moment later the policy report says it would be refused in prod. This is how you introduce policies without breaking anyone.",
      tts="Step five: audit mode. try dot S H sandbox starts the same Docker Hub image in the sandbox namespace. This time it is admitted, "
          "and a moment later the policy report says it would be refused in prod. This is how you introduce policies without breaking anyone."),
    S("Then scan starts an old nginx, version 1.21.0, and waits for Trivy Operator. On my laptop it found twenty seven critical and one hundred thirty four high vulnerabilities.",
      tts="Then scan starts an old engine x, version 1 point 21 point 0, and waits for Trivy Operator. On my laptop it found twenty seven critical and one hundred thirty four high vulnerabilities."),
    S("And alerts shows what Prometheus thinks. Untrusted workload blocked is firing, because of your attacks in step four. "
      "And the vulnerability alert is pending: even today's nginx 1.29 from the sandbox exercise has six critical findings. It fires after five minutes.",
      tts="And alerts shows what Prometheus thinks. Untrusted workload blocked is firing, because of your attacks in step four. "
          "And the vulnerability alert is pending: even today's engine x 1 point 29 from the sandbox exercise has six critical findings. It fires after five minutes."),
])

scene(None, "Hands-on lab · step 6", "Dashboard, your own commands, clean up", terminal([
    (0, "$ scripts/try.sh dashboard", "cmd"),
    (0, "==> Grafana: http://localhost:3000 (Ctrl+C to stop)", "ok"),
    (1, "$ source scripts/lib.sh            # k = kubectl, tb = any tool in the toolbox", "cmd"),
    (1, "$ k -n prod get pods", "cmd"),
    (1, "$ tb cosign tree ghcr.io/sufyanahmadkamboh/storefront-api@sha256:cb9b332c…", "cmd"),
    (1, "└── 💾 Attestations for an image tag: …:sha256-cb9b332ce38c….att   (3 entries)", "out"),
    (1, "└── 🔐 Signatures for an image tag: …:sha256-cb9b332ce38c….sig     (1 entry)", "out"),
    (2, "# study/15-hands-on-labs.md: 9 labs — break a policy and let the tests catch it,", "dim"),
    (2, "#   break an alert and let promtool catch it, fix a vulnerable workflow, follow a full release in a fork", "dim"),
    (3, "$ scripts/try.sh clean", "cmd"),
    (3, "$ kind delete cluster --name supply-chain", "cmd"),
], "bash"), [
    S("Step six. try dot S H dashboard opens Grafana on localhost, port 3000, with the same dashboard you saw earlier.",
      tts="Step six. try dot S H dashboard opens Grafana on localhost, port 3000, with the same dashboard you saw earlier."),
    S("To run your own commands, source lib dot S H. Then k is kubectl, and tb runs any tool from the toolbox, for example cosign tree, to see every signature and attestation attached to the image.",
      tts="To run your own commands, source lib dot S H. Then k is kube control, and T B runs any tool from the toolbox, for example co-sign tree, to see every signature and attestation attached to the image."),
    S("When you are ready for more, the study guide has nine labs. You break a policy and let the tests catch it, break an alert and let prom tool catch it, "
      "fix a vulnerable workflow, and follow a full signed release in your own fork."),
    S("When you are done, clean up the exercise pods, and delete the cluster with kind. Your laptop is back to normal."),
])

scene("Use it in production", "Production rollout · part 1", "From this repo to your cluster", checklist([
    (1, "1", "Make it yours", "change the image name + trusted identity: 3 policy files, release.yaml, scripts/e2e.sh"),
    (2, "2", "Protect the trust anchor", "branch protection on main, required reviews + checks, CODEOWNERS for workflows and policies"),
    (3, "3", "Install Kyverno with Helm", "run 3+ admission controller replicas: the webhook fails closed"),
    (4, "4", "Start in audit mode", "label namespaces audit=true, read PolicyReports for 1–2 weeks, fix findings"),
]), [
    S("Now, how do you use this in your own production? Here is the plan, step by step."),
    S("Step one: make it yours. Change the image name and the trusted identity in the three policy files, in the release workflow, and in the test script."),
    S("Step two: protect the trust anchor. Turn on branch protection for main, with required reviews and required checks, and use CODEOWNERS for the workflows and the policies. "
      "Whoever can change release dot yaml on main can release anything.",
      tts="Step two: protect the trust anchor. Turn on branch protection for main, with required reviews and required checks, and use code owners for the workflows and the policies. "
          "Whoever can change release dot yammel on main can release anything."),
    S("Step three: install Kyverno with Helm. In production, run at least three admission controller replicas, because the webhook fails closed.",
      tts="Step three: install Kai-verno with Helm. In production, run at least three admission controller replicas, because the webhook fails closed."),
    S("Step four: start in audit mode. Label your namespaces with audit, read the policy reports for one or two weeks, and fix what they find."),
])
scene(None, "Production rollout · part 2", "Enforce, observe, and keep it simple", checklist([
    (0, "5", "Enforce gradually", "switch the label to enforce=true, one namespace at a time, most critical first"),
    (1, "6", "Wire up the alerts", "route the 3 alerts to on-call, put the dashboard in front of the team"),
    (2, "7", "Emergencies", "a reviewed, time-limited PolicyException in git; never delete the policies"),
    (3, "8", "Day-2 operations", "rollback = git revert · no keys to rotate · distrust a build by changing the identity"),
]), [
    S("Step five: switch to enforce gradually, one namespace at a time, starting with the most critical one."),
    S("Step six: route the three alerts to your on call channel, and put the dashboard in front of the team."),
    S("Step seven: for real emergencies, use a reviewed, time limited policy exception in git. Never delete the policies."),
    S("And step eight, day two operations: a rollback is a git revert, there are no signing keys to rotate, and to stop trusting a build, you change the identity in the policy."),
])

# ---------------------------------------------------------------- 28. Limits
scene("Limitations & next steps", "Honest limits", "What this does not do (yet)", grid([
    card(0, "🏗️", "SLSA Build L2-style", "the build job also signs; L3 needs isolated provenance (slsa-github-generator)", "amber"),
    card(1, "👑", "Cluster admins", "admission control can't stop someone who can delete the policies", "amber"),
    card(1, "🌐", "Public Sigstore", "air-gapped clusters need a private Fulcio and Rekor", "amber"),
    card(2, "📦", "Classic signature format", "switch to Sigstore bundles once Kyverno reads them", "blue"),
    card(2, "🧱", "Base image signatures", "verify the distroless signature during the build", "blue"),
], cols=2), [
    S("Let us be honest about the limits. The build job also signs, so this is SLSA level two style provenance, not level three. The next step is the official SLSA GitHub generator.",
      tts="Let us be honest about the limits. The build job also signs, so this is salsa level two style provenance, not level three. The next step is the official salsa GitHub generator."),
    S("Admission control does not protect against cluster admins, who can delete the policies. And the public Sigstore service is used, so air gapped clusters need a private Sigstore."),
    S("Also on the list: the new Sigstore bundle format once Kyverno supports it, and verifying the signatures of the base images during the build.",
      tts="Also on the list: the new Sigstore bundle format once Kai-verno supports it, and verifying the signatures of the base images during the build."),
])

# ---------------------------------------------------------------- 29. Outro
scene("Summary & resources", "Thanks for watching", "Only code you can prove runs in production", grid([
    card(0, "🔏", "Proof, not trust", "signature + provenance + scan + SBOM, checked for every pod", "ok"),
    card(0, "🧪", "Proven on every release", "the pipeline attacks a fresh cluster before it ships", "ok"),
    card(1, "💻", "Code + docs", REPO, "blue"),
    card(1, "📚", "Free study guide", "60-page PDF, 9 labs, 25 interview questions", "blue"),
    card(2, "💬", "Your turn", "with your registry password, could someone run code in your cluster?", "amber"),
    card(2, "🔔", "More real DevOps projects", "subscribe so you don't miss the next one", "amber"),
], cols=2), [
    S("That is the project. Production now runs only code it can prove came from your pipeline, and every release proves it again by attacking itself."),
    S("The code, the documentation and a free sixty page study guide, with labs and interview questions, are linked in the description. "
      "Clone it, run platform up, and try the attacks yourself."),
    S("Now I would like to hear from you: with your registry password, could someone run their code in your cluster? Tell me in the comments. "
      "And if this helped, subscribe for more real DevOps projects. Thanks for watching."),
])
