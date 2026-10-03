# 6. Signing with Sigstore (cosign, Fulcio, Rekor)

## What is it?

**Sigstore** is an open-source project (Linux Foundation / OpenSSF) for signing software without managing keys. It has three parts:

| Part | Job |
|---|---|
| **cosign** | the command-line tool that signs and verifies images and attestations |
| **Fulcio** | a certificate authority that issues **short-lived certificates** (about 10 minutes) to an identity proven by an OIDC token |
| **Rekor** | a public, append-only **transparency log**: every signature is recorded there, with a timestamp |

## Why this project uses it

A classic signing key is a secret that can be stolen. Whoever has it can sign anything forever. With **keyless signing** there is no long-lived key: the release job proves *who it is* to Fulcio with GitHub's OIDC token, gets a certificate valid for minutes, signs, and the signature is logged in Rekor. The certificate names the **exact workflow file and git ref**, so the verifier can demand: "signed by `release.yaml` on `main` of this repository".

**Alternatives:** cosign with a stored key pair or a cloud KMS key; Notary v2 / Notation (X.509 certificates, common with Azure); GPG-signed images (rarely supported by runtimes).

## How it works

1. The job requests an OIDC token from GitHub (allowed by `id-token: write`).
2. cosign creates a fresh key pair in memory and sends the public key + token to **Fulcio**.
3. Fulcio checks the token with GitHub and issues a certificate whose **subject** is the workflow identity, for example
   `https://github.com/sufyanahmadkamboh/sufyan-devops-secure-supply-chain/.github/workflows/release.yaml@refs/heads/main`
   and whose **issuer** is `https://token.actions.githubusercontent.com`.
4. cosign signs the image **digest**, uploads the signature + certificate to the registry, and records it in **Rekor**.
5. The private key is thrown away.

To verify, you do not need any key: check that the certificate chains to Fulcio, that the subject and issuer are the ones you expect, that the signature matches the digest, and that the Rekor entry proves the signature was made while the certificate was valid.

### Why the identity is a workflow file

Every workflow in the repository can get an OIDC token, but each token says *which* workflow it came from. Trusting `release.yaml@refs/heads/main` (and nothing else) means an injected workflow, a pull request branch, or the e2e test workflow can sign images, but those signatures name a different identity and are refused.

### Why the classic signature format

cosign 3 writes signatures in a new "bundle" format by default. In this project's tests, Kyverno 1.19's ImageValidatingPolicy verified classic signatures (`.sig` / `.att` artifacts) but did not find signatures in the new format. So the pipeline signs with `--new-bundle-format=false --use-signing-config=false` (see [docs/troubleshooting.md](../docs/troubleshooting.md)).

## Where it is integrated

[`.github/workflows/release.yaml`](../.github/workflows/release.yaml):

```yaml
      - name: Sign and attest (keyless, recorded in Rekor)
        env:
          DIGEST: ${{ steps.push.outputs.digest }}
        run: |
          legacy=(--new-bundle-format=false --use-signing-config=false --yes)
          cosign sign "${legacy[@]}" "${IMAGE}@${DIGEST}"
```

Right after, the workflow verifies what it published with the same identity rule the cluster uses:

```bash
          id="${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/.github/workflows/release.yaml@refs/heads/main"
          cosign verify --certificate-identity "$id" \
            --certificate-oidc-issuer https://token.actions.githubusercontent.com "${IMAGE}@${DIGEST}" > /dev/null
```

The cluster side, [`policies/base/verify-images.yaml`](../policies/base/verify-images.yaml):

```yaml
  attestors:
    - name: release-workflow
      cosign:
        keyless:
          identities:
            - issuer: https://token.actions.githubusercontent.com
              subject: https://github.com/sufyanahmadkamboh/sufyan-devops-secure-supply-chain/.github/workflows/release.yaml@refs/heads/main
        ctlog:
          url: https://rekor.sigstore.dev
```

## Try it

```bash
source scripts/lib.sh
ID=https://github.com/sufyanahmadkamboh/sufyan-devops-secure-supply-chain/.github/workflows/release.yaml@refs/heads/main
IMG=ghcr.io/sufyanahmadkamboh/storefront-api@sha256:<digest from deploy/prod/kustomization.yaml>
tb cosign verify --certificate-identity "$ID" --certificate-oidc-issuer https://token.actions.githubusercontent.com "$IMG" | tb jq '.[0].optional'
# now ask for a different identity: verification fails
tb cosign verify --certificate-identity "${ID/release.yaml/e2e.yaml}" --certificate-oidc-issuer https://token.actions.githubusercontent.com "$IMG"
```

The `optional` block shows the Fulcio certificate claims: subject, issuer, repository, commit SHA, workflow ref.

## Common mistakes

- Verifying with `--certificate-identity-regexp '.*'`: that accepts *anyone* who can get a Sigstore certificate. Pin the exact identity.
- Signing a tag instead of a digest.
- Trusting "any workflow of my repository": an injected workflow then becomes trusted.
- Forgetting the Rekor URL in the Kyverno attestor when the transparency log is not ignored ("rekor URL must be provided").

## Check yourself

1. What is stored as a secret for signing in this project?
2. Which two values does the cluster compare in the certificate?
3. Why would trusting the identity regexp `.*/sufyan-devops-secure-supply-chain/.*` be a bad idea?

### Answers

<details><summary>Answers</summary>

1. Nothing. The signing key exists only in memory for one signature; the identity comes from GitHub's OIDC token via Fulcio.
2. The subject (the workflow file and ref: `.../release.yaml@refs/heads/main`) and the issuer (`https://token.actions.githubusercontent.com`).
3. It trusts every workflow and every branch of the repository, including an injected malicious workflow, pull request branches and the e2e workflow. Only the release workflow on main should be trusted.

</details>
