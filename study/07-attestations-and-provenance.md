# 7. Attestations and SLSA provenance

## What is it?

A signature says "this identity vouches for this digest". An **attestation** says *something specific* about the digest and is signed too: "this is its SBOM", "this is its vulnerability scan", "this is how it was built". The common format is an **in-toto statement**:

```json
{
  "_type": "https://in-toto.io/Statement/v1",
  "subject": [{"name": "ghcr.io/...", "digest": {"sha256": "..."}}],
  "predicateType": "https://slsa.dev/provenance/v1",
  "predicate": { ... the actual content ... }
}
```

**SLSA** (Supply-chain Levels for Software Artifacts) defines a standard **provenance** predicate: which source, which build process, which run produced the artifact.

## Why this project uses it

- The cluster can check not only *who* signed, but *what* they claimed: built from this repository's `main`, scan clean, SBOM present.
- Because attestations are signed by the release identity, an attacker cannot hand in a forged "clean scan" or "built from main" document.

**Alternatives:** GitHub's built-in artifact attestations (stored in GitHub's attestation API), the SLSA GitHub generator (builds provenance in an isolated reusable workflow for SLSA Build L3), Tekton Chains.

## How it works

`cosign attest --type <type> --predicate <file> <image@digest>` wraps the predicate into an in-toto statement whose subject is the digest, signs it with the same keyless flow as chapter 6, and stores it next to the image. This project creates three:

| `--type` | predicateType | Content |
|---|---|---|
| `slsaprovenance1` | `https://slsa.dev/provenance/v1` | repository, ref, workflow path, commit, builder, run URL |
| `vuln` | `https://cosign.sigstore.dev/attestation/vuln/v1` | Trivy's scan result |
| `cyclonedx` | `https://cyclonedx.org/bom` | the SBOM |

## Where it is integrated

The provenance predicate is written by [`scripts/ci/provenance.sh`](../scripts/ci/provenance.sh) from facts the runner provides:

```bash
repo_url="$GITHUB_SERVER_URL/$GITHUB_REPOSITORY"
...
    buildDefinition: {
      buildType: "https://github.com/sufyanahmadkamboh/sufyan-devops-secure-supply-chain/buildtypes/docker-build/v1",
      externalParameters: {
        workflow: {repository: $repo, ref: $ref, path: $path}
      },
      ...
      resolvedDependencies: [
        {uri: ("git+" + $repo + "@" + $ref), digest: {gitCommit: $sha}}
      ]
    },
    runDetails: {
      builder: {id: $builder},
      metadata: {invocationId: $run, startedOn: $started, finishedOn: $finished}
    }
```

Signed in [`.github/workflows/release.yaml`](../.github/workflows/release.yaml):

```bash
cosign attest "${legacy[@]}" --type slsaprovenance1 --predicate provenance.json "${IMAGE}@${DIGEST}"
cosign attest "${legacy[@]}" --type vuln --predicate vuln.json "${IMAGE}@${DIGEST}"
cosign attest "${legacy[@]}" --type cyclonedx --predicate sbom.cdx.json "${IMAGE}@${DIGEST}"
```

Checked in [`policies/base/verify-images.yaml`](../policies/base/verify-images.yaml). Note `extractPayload(...)` returns the whole statement, so the content is under `.predicate`:

```yaml
    - expression: >-
        images.containers.all(image,
          extractPayload(image, attestations.provenance).predicate.buildDefinition.externalParameters.workflow.repository
            == "https://github.com/sufyanahmadkamboh/sufyan-devops-secure-supply-chain"
          && extractPayload(image, attestations.provenance).predicate.buildDefinition.externalParameters.workflow.ref
            == "refs/heads/main")
      message: provenance does not show a build of this repository's main branch
```

### An honest limit

The provenance is generated and signed in the same job that builds the image. That is good evidence (it is bound to the release identity), but it is not **SLSA Build Level 3**, which requires that the build cannot influence the provenance (an isolated builder). The [architecture decision log](../docs/architecture.md) records this trade-off (decision 14). Moving provenance generation into an isolated reusable workflow, such as the SLSA GitHub generator, would close that gap.

## Try it

```bash
source scripts/lib.sh
ID=https://github.com/sufyanahmadkamboh/sufyan-devops-secure-supply-chain/.github/workflows/release.yaml@refs/heads/main
IMG=ghcr.io/sufyanahmadkamboh/storefront-api@sha256:<digest from deploy/prod/kustomization.yaml>
tb cosign verify-attestation --type slsaprovenance1 \
  --certificate-identity "$ID" --certificate-oidc-issuer https://token.actions.githubusercontent.com "$IMG" \
  | tb jq -r '.payload' | base64 -d | tb jq '.predicate'
```

You will see the commit SHA and the run URL: click it in GitHub to see the exact run that built what you are looking at.

## Common mistakes

- Checking that an attestation *exists* but not *who signed it*.
- Reading `extractPayload(...).result` instead of `.predicate.result` (the error is "no such key").
- Believing provenance written by the build itself is tamper-proof against a compromised build step. It proves the identity, not the build's isolation.

## Check yourself

1. What is the difference between a signature and an attestation?
2. Where in the in-toto statement is the scan result?
3. Why can't the e2e workflow simply sign a fake "clean" vulnerability attestation for a bad image?

### Answers

<details><summary>Answers</summary>

1. A signature only binds an identity to a digest. An attestation is a signed statement with typed content (provenance, scan, SBOM) about that digest.
2. In `predicate.scanner.result`, inside the statement that `extractPayload` returns.
3. It can create and sign one, but the signature names the e2e workflow identity. The policy only accepts attestations signed by `release.yaml@refs/heads/main`, so the fake report is ignored and the image is refused. The e2e test does exactly this (imposter scenario).

</details>
