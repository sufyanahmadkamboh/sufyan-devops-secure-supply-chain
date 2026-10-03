# 4. SBOM (Software Bill of Materials)

## What is it?

An **SBOM** is the list of ingredients of a piece of software: every package, library and module inside an image, with versions and licences. **CycloneDX** and **SPDX** are the two standard formats. **Syft** is a tool that looks inside an image and writes its SBOM.

## Why this project uses it

- When a new vulnerability is announced ("library X before 1.4.2 is affected"), the SBOM answers in seconds: *is it inside anything we run?*
- Regulations increasingly require SBOMs (the EU Cyber Resilience Act, US federal procurement rules).
- Here the SBOM is **signed** as an attestation, so it cannot be swapped for a cleaner-looking one.

**Alternatives:** Trivy can also generate SBOMs; `docker sbom` (uses Syft); language-specific tools (`cyclonedx-gomod`). Syft was chosen because it covers OS packages and Go binaries in one pass and outputs both standards.

## How it works

Syft reads the image layers, recognises package databases (Debian dpkg status, Go build info embedded in binaries, Python metadata...) and writes a JSON document listing **components**. For a distroless Go image the list is short: the Go modules compiled in, the Go standard library, and the few Debian files in the distroless base.

## Where it is integrated

In [`.github/workflows/release.yaml`](../.github/workflows/release.yaml), right after the push (so the SBOM describes exactly the published digest):

```yaml
        run: |
          syft scan --quiet "registry:${IMAGE}@${DIGEST}" -o cyclonedx-json=sbom.cdx.json
          ...
          jq '{components: (.components | length)}' sbom.cdx.json
```

Then it is signed and attached to the image:

```bash
cosign attest "${legacy[@]}" --type cyclonedx --predicate sbom.cdx.json "${IMAGE}@${DIGEST}"
```

The cluster requires it: [`policies/base/verify-images.yaml`](../policies/base/verify-images.yaml) declares the attestation type `https://cyclonedx.org/bom` and the rule "no signed SBOM from the release workflow" denies Pods without one. The SBOM is also uploaded as part of the `supply-chain-evidence` artifact of every release run.

## Try it

```bash
ID=https://github.com/sufyanahmadkamboh/sufyan-devops-secure-supply-chain/.github/workflows/release.yaml@refs/heads/main
IMG=ghcr.io/sufyanahmadkamboh/storefront-api@sha256:<digest from deploy/prod/kustomization.yaml>
source scripts/lib.sh
tb cosign verify-attestation --type cyclonedx \
  --certificate-identity "$ID" --certificate-oidc-issuer https://token.actions.githubusercontent.com "$IMG" \
  | tb jq -r '.payload' | base64 -d | tb jq '.predicate.components[] | "\(.name) \(.version)"' | head -20
```

## Common mistakes

- Generating the SBOM from the source directory instead of the built image (you miss the base image contents).
- Keeping SBOMs as unsigned files on a wiki: nobody can prove which image they describe.
- Generating an SBOM and never using it. Its value comes from searching it when a CVE is announced.

## Check yourself

1. Why is the SBOM made after the push, from `registry:${IMAGE}@${DIGEST}`?
2. What does the admission policy check about the SBOM?
3. Give one practical use of an SBOM during an incident.

### Answers

<details><summary>Answers</summary>

1. So that it describes exactly the content that was published under that digest, the same thing that gets signed and deployed.
2. That a CycloneDX attestation exists for the image and is signed by the release workflow identity.
3. When a new CVE in a library is announced, search the SBOMs of running images to find out within seconds which services include the affected version.

</details>
