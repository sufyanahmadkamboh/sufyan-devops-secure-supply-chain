# 2. Software supply chain attacks

## What is it?

The **software supply chain** is everything between a developer's keyboard and the program running in production: source code, dependencies, base images, the CI system and its plugins, the registry, the deployment tool. A **supply chain attack** compromises one of these links, so that production runs the attacker's code while everyone believes it is their own.

## Why this project exists

Most clusters trust *locations*: "images from our registry" or "whatever Argo CD deploys from our repo". Every one of those locations can be written to by more people and machines than you think. This project replaces trust in locations with **verifiable proof of origin**.

## How the attacks work

| Attack | What the attacker does | Real-world pattern |
|---|---|---|
| **Stolen registry token** | pushes their own image into your repository, maybe under an existing tag | leaked CI secrets, a developer laptop compromise |
| **Moved tag** | points a tag (`:1.2`, `:latest`, or a GitHub Action's `@v4`) at different content | 2025–2026 incidents where popular GitHub Action tags were redirected to malicious commits |
| **Tampered image** | takes your real image, adds a layer with a backdoor, pushes it back | anyone with registry write access |
| **Injected workflow** | adds a new workflow file to a repository that runs with the repo's permissions | a 2026 campaign pushed malicious workflows into thousands of repositories within hours |
| **Template injection** | puts shell code into a PR title or branch name that a workflow pastes into a `run:` step | the "Cordyceps" class of workflow flaws |
| **Malicious commit to deploy files** | changes the image in the GitOps repository | a stolen deploy key or a compromised bot account |
| **Vulnerable dependency** | not an attack by itself, but a known hole someone will use later | a CVE published after you deployed |

## Why "it came from our registry" proves nothing

A registry stores whatever an authenticated client pushes. It does not know *who built* the content or *from which code*. The same is true for git: Argo CD deploys whatever is committed. So the proof must travel **with the image**, be **tied to its exact content** (the digest), and identify the **build process**, not a person or a server.

That is what signatures and attestations do (chapters 6 and 7), and what admission control enforces (chapter 8).

## Where it is integrated

The [architecture document](../docs/architecture.md) has a trust-boundary table listing each attacker capability and what stops it. The end-to-end test, [`scripts/e2e.sh`](../scripts/e2e.sh), simulates several of these attacks for real on every release:

```bash
# unsigned: a completely different image pushed into our repository
crane copy docker.io/library/busybox:1.37 $IMAGE:e2e-unsigned-$RUN
# tampered: the trusted image plus one extra layer (a 'backdoor' file), same name
crane append -b $TRUSTED -f /tmp/bd.tar -t $IMAGE:e2e-tampered-$RUN
```

## Try it

Look at the registry and notice there is nothing in a tag that tells you who built the image:

```bash
source scripts/lib.sh
tb crane config ghcr.io/sufyanahmadkamboh/storefront-api:<tag> | tb jq .config.Labels
```

The labels (`org.opencontainers.image.source`, `...revision`) are just text in the image. Anyone can write any label. Compare that with chapter 6, where the identity comes from a certificate issued to the build.

## Common mistakes

- Treating image labels or tag names as proof of origin.
- Signing images with a long-lived private key stored as a CI secret. Whoever steals the secret can sign anything, which brings back the original problem.
- Protecting the registry but not the CI workflows that have write access to it.

## Check yourself

1. Name three different ways an attacker could get their code into a cluster that trusts "images from our registry".
2. Why must the proof of origin be tied to the digest?
3. Why is a malicious commit to the deploy files dangerous in plain GitOps?

### Answers

<details><summary>Answers</summary>

1. Push with a stolen registry token; move a tag to different content; inject a workflow that builds and pushes from the repo; tamper with an existing image and push it back.
2. Because the digest identifies the exact content. A proof tied to a tag or a name could be reused for different content.
3. GitOps tools apply whatever is in git. Without admission checks, changing one image line in a manifest is enough to run any image in production.

</details>
