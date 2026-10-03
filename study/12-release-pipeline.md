# 12. The release pipeline, step by step

## What is it?

Two workflows do all the work in GitHub Actions:

| Workflow | Runs on | Job |
|---|---|---|
| [`ci.yaml`](../.github/workflows/ci.yaml) | every pull request and push | static checks: the workflows themselves, Go code, shell scripts, Dockerfiles, manifests, policies, alert rules |
| [`release.yaml`](../.github/workflows/release.yaml) | push to `main` (relevant paths) | build, scan, push, SBOM, sign, attest, verify, **attack test**, promote |

The third file, [`e2e.yaml`](../.github/workflows/e2e.yaml), is a **reusable workflow** called by `release.yaml` (chapter 13).

## Why it is built this way

- **Gate before publish.** The vulnerability gate runs before the push: a bad image never reaches the registry.
- **Everything about one digest.** After the push, every step (SBOM, scan report, provenance, signature) refers to `${IMAGE}@${DIGEST}`, never to a tag.
- **Verify what you published.** The job checks its own output with the same identity rule the cluster uses, so a broken signing step fails here, not in production.
- **Attack test before promote.** A change that weakens the defences (a broken policy, a wrong identity) is caught before the digest reaches `deploy/prod`.
- **Least privilege per job.** `permissions: {}` at the top; each job asks only for what it needs.

## How it works

```
push to main
   |
   v
build  (contents: read, packages: write, id-token: write)
   checkout (no credentials kept)
   install cosign, syft, trivy by checksum
   docker build (unit tests run inside the build stage)
   trivy gate: no fixable CRITICAL/HIGH          --> fail = stop
   push, read back the digest
   SBOM (syft), scan report (trivy), provenance (script)
   cosign sign + 3 x cosign attest (keyless)
   cosign verify + verify-attestation (release identity)
   upload "supply-chain-evidence" artifact
   |
   v
e2e    (reusable e2e.yaml: kind cluster + attack scenarios)  --> fail = stop
   |
   v
promote (contents: write)
   sed the digest into deploy/prod/kustomization.yaml, commit, push
   |
   v
Argo CD syncs prod; Kyverno verifies the pods
```

## Where it is integrated

Top of [`release.yaml`](../.github/workflows/release.yaml):

```yaml
permissions: {}

concurrency:
  group: release
  cancel-in-progress: false
```

`cancel-in-progress: false`: a release that already signed and is in its attack test is never killed halfway by the next push.

The build job's permissions, each with its reason:

```yaml
    permissions:
      contents: read
      packages: write   # push the image and its signatures to GHCR
      id-token: write   # keyless signing: GitHub OIDC token -> Fulcio certificate
```

Getting the digest from the push (never trust the tag afterwards):

```bash
docker push --quiet "${IMAGE}:sha-${GITHUB_SHA::12}"
ref="$(docker inspect --format '{{index .RepoDigests 0}}' "${IMAGE}:sha-${GITHUB_SHA::12}")"
echo "digest=${ref##*@}" >> "$GITHUB_OUTPUT"
```

The promote job, which only runs when `build` and `e2e` both succeeded:

```yaml
  promote:
    name: Promote to production (GitOps)
    needs: [build, e2e]
    ...
        run: |
          sed -i -E "s|(    digest: )sha256:[a-f0-9]{64}|\1${DIGEST}|" deploy/prod/kustomization.yaml
          git diff --quiet && { echo "already deployed"; exit 0; }
          ...
          git commit -am "deploy: storefront-api ${DIGEST:7:12}"
          git push origin HEAD:main
```

Note the `paths:` filter on the trigger: changes to `deploy/prod` are **not** in it. The promote commit therefore does not start a new release (no loop).

Tools come from [`scripts/ci/install-tools.sh`](../scripts/ci/install-tools.sh), which downloads pinned versions and checks their SHA-256 checksums, instead of using third-party "setup" actions (chapter 3).

## Try it

You cannot sign as `release.yaml@main` from your laptop (that is the point). What you can do:

```bash
# read the pipeline order and permissions
grep -nE "^  [a-z]+:|permissions|needs:|id-token" .github/workflows/release.yaml
# run the same static checks CI runs
scripts/ci/check-pinned-actions.sh
docker build -q -t ssc-toolbox:dev tools/toolbox
docker run --rm -v "$PWD:/work" -w /work ssc-toolbox:dev kyverno test policies/tests
# in a fork: push to main and open the Actions tab; the "supply-chain-evidence" artifact holds the SBOM, scan and provenance
```

## Common mistakes

- Pushing first and scanning later: a vulnerable image is already published and could be pulled.
- Signing `image:tag`: what you signed and what you deploy can differ.
- Giving `id-token: write` or `contents: write` to the whole workflow instead of the jobs that need them.
- Letting the deploy commit re-trigger the release (endless loop), or letting a newer push cancel a half-finished release.

## Check yourself

1. Why does the Trivy gate run before `docker push`?
2. Which job has `contents: write`, and why only that one (plus e2e)?
3. What prevents the promote commit from starting another release?

### Answers

<details><summary>Answers</summary>

1. So that an image with fixable CRITICAL or HIGH vulnerabilities never reaches the registry, where someone could pull or deploy it.
2. `promote` (to commit the new digest to `deploy/prod`) and `e2e` (to push a temporary GitOps branch). `build` only reads the code; it cannot change the repository even if a build step were compromised.
3. The `paths:` filter on the `push` trigger does not include any path under `deploy/prod/`, so a commit that only changes the digest does not match.

</details>
