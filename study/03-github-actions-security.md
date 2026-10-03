# 3. GitHub Actions security

## What is it?

**GitHub Actions** runs workflows (YAML files in `.github/workflows/`) on GitHub-hosted machines when something happens in a repository: a push, a pull request, a schedule. Workflows are made of **jobs**, jobs of **steps**, and steps either run shell commands (`run:`) or use reusable components called **actions** (`uses:`).

## Why it matters here

In this project the CI system is not just a helper: the release workflow's **identity is the trust anchor**. Production admits only images signed by `.github/workflows/release.yaml` on `refs/heads/main`. So the workflows themselves must be hard to abuse.

**Alternatives:** GitLab CI (similar OIDC identity features), Jenkins (no built-in workload identity; keyless signing needs extra setup), Tekton Chains (signs in-cluster).

## How it works

### Permissions of GITHUB_TOKEN
Every job gets a token. By default it can be broad. The safe pattern: **deny everything at the top, grant per job only what it needs.**

### OIDC tokens
With `id-token: write`, a job can ask GitHub for a short-lived **OIDC token**: a signed statement such as "this is repository X, workflow file Y, ref Z, run N". Other services (here: Sigstore's Fulcio) trust GitHub's signature and issue credentials based on those claims. No password is stored.

### Pinning actions to commit SHAs
`uses: actions/checkout@v7` follows a tag, which can be moved. `uses: actions/checkout@3d3c42e5...` follows one commit, which cannot change. Keep the version as a comment for humans.

### Template injection
`run: echo "${{ github.event.pull_request.title }}"` pastes attacker-controlled text into a shell script. Pass such values through `env:` instead, where the shell treats them as data.

### persist-credentials
`actions/checkout` leaves the token in `.git/config` unless `persist-credentials: false`. Later steps (or a malicious dependency) could read it.

### Linters for workflows
- **actionlint** checks syntax, expressions and shell scripts in workflows.
- **zizmor** looks for security problems: template injection, excessive permissions, persisted credentials, unpinned actions.

### Process controls
- **Branch protection**: no direct pushes to `main`, reviews required.
- **CODEOWNERS**: certain paths need approval from named owners.
- **Dependabot**: proposes updates for pinned SHAs and digests, so pinning does not mean "stuck on old versions".

## Where it is integrated

Every workflow starts with `permissions: {}` and grants per job. From [`.github/workflows/release.yaml`](../.github/workflows/release.yaml):

```yaml
permissions: {}
...
  build:
    permissions:
      contents: read
      packages: write   # push the image and its signatures to GHCR
      id-token: write   # keyless signing: GitHub OIDC token -> Fulcio certificate
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
```

Values from GitHub contexts go through `env:`, never directly into `run:`:

```yaml
      - name: SBOM, vulnerability report and provenance
        env:
          DIGEST: ${{ steps.push.outputs.digest }}
        run: |
          syft scan --quiet "registry:${IMAGE}@${DIGEST}" -o cyclonedx-json=sbom.cdx.json
```

Tools are installed from official downloads with a pinned SHA-256 instead of third-party actions ([`scripts/ci/install-tools.sh`](../scripts/ci/install-tools.sh)):

```bash
fetch() {  # url sha256 file
  curl -fsSL --retry 3 -o "$work/$3" "$1"
  echo "$2  $work/$3" | sha256sum -c - >/dev/null
}
```

A script fails the build if any action is not pinned to a commit ([`scripts/ci/check-pinned-actions.sh`](../scripts/ci/check-pinned-actions.sh)):

```bash
  if [[ ! "$ref" =~ @[0-9a-f]{40}$ ]]; then
    echo "NOT PINNED: $file -> $ref"
    bad=1
  fi
```

The `ci` workflow ([`.github/workflows/ci.yaml`](../.github/workflows/ci.yaml)) runs that script, actionlint, and zizmor (installed with `--require-hashes` from [`tools/zizmor-requirements.txt`](../tools/zizmor-requirements.txt)). [`.github/CODEOWNERS`](../.github/CODEOWNERS) puts workflows, policies and platform files under owner review, and [`.github/dependabot.yml`](../.github/dependabot.yml) keeps actions, Docker base images and Go modules up to date.

## Try it

```bash
bash scripts/ci/check-pinned-actions.sh
# then change one "uses:" line to @v7 and run it again: it fails and names the file
docker run --rm -v "$PWD:/repo" -w /repo rhysd/actionlint:1.7.12
pip install zizmor==1.30.1 && zizmor --min-severity low .github/workflows
```

## Common mistakes

- `permissions: write-all` "to make it work".
- Pinning to a tag and believing it is pinned.
- Using `pull_request_target` with a checkout of the PR's code (it runs untrusted code with write permissions).
- Giving `id-token: write` to every job: any job with it can obtain a signing identity.

## Check yourself

1. Why does the `promote` job have `contents: write` but no `id-token: write`?
2. What is wrong with `run: echo "${{ github.head_ref }}"`?
3. If actions are pinned to SHAs, how do you get security updates?

### Answers

<details><summary>Answers</summary>

1. It only commits a digest to git. It never signs anything, so it must not be able to obtain a signing identity.
2. The branch name is attacker-controlled and pasted into a shell script before it runs (template injection). Pass it via `env:` and use `"$VAR"`.
3. Dependabot proposes pull requests that update the SHA (with the new version in the comment); they go through review and CI like any other change.

</details>
