# 1. Containers and images

## What is it?

A **container image** is a packaged program plus everything it needs to run (libraries, files, settings), stored as a set of read-only **layers**. A **container** is a running instance of an image. A **registry** is a server that stores images (Docker Hub, GitHub Container Registry `ghcr.io`, AWS ECR...).

## Why it matters for this project

Everything this project protects is an image. To understand how an image can be swapped or tampered with, you need to know how images are named and stored.

**Alternatives** to container images for shipping software: virtual machine images, OS packages (deb/rpm), plain binaries. Kubernetes runs containers, so images are the unit here.

## How it works

### Layers and the manifest
An image is a list of layers (tar files) plus a configuration, described by a small JSON document called the **manifest**. Each layer and the manifest are identified by the SHA-256 hash of their content.

### Tags vs digests
An image can be referenced in two ways:

| Reference | Example | Can it change? |
|---|---|---|
| **tag** | `ghcr.io/sufyanahmadkamboh/storefront-api:sha-df34de356ff1` | **yes**, anyone with push rights can point the tag at different content |
| **digest** | `ghcr.io/sufyanahmadkamboh/storefront-api@sha256:e9b0f3...` | **no**, the digest *is* the hash of the content; different content = different digest |

A tag is like a shelf label; a digest is like a fingerprint. Security decisions must be made on digests.

### Registries
`docker push` uploads layers and the manifest; the registry answers with the digest. Signatures and attestations made by cosign are stored in the same registry, next to the image, as extra artifacts (tags like `sha256-<digest>.sig` and `.att`).

### Distroless images
A **distroless** image contains only the program and the minimum runtime files: no shell, no package manager, no extra tools. Less inside means fewer vulnerabilities and nothing for an attacker to use after breaking in.

## Where it is integrated

The service is a small Go program, [`app/main.go`](../app/main.go), with endpoints `/healthz`, `/version` and `/api/products`. The [`app/Dockerfile`](../app/Dockerfile) builds it in two stages, with both base images **pinned by digest**:

```dockerfile
# Base images are pinned by digest: a tag can be moved to different content, a digest cannot.
FROM golang:1.27.1-trixie@sha256:3b77fc618ec235a1ab412de7737f120dd507c57e8d87de4cbb7994fb94275ed5 AS build
...
RUN go test ./... \
 && CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -trimpath -buildvcs=false \
      -ldflags="-s -w -buildid= -X main.version=${VERSION} -X main.commit=${COMMIT}" -o /out/storefront-api .

# No shell, no package manager, runs as uid 65532.
FROM gcr.io/distroless/static-debian13:nonroot@sha256:e2e927ec666bae08560abb3c55d0659eceabb657f56b6782ab500a9fc7f555e3
COPY --from=build /out/storefront-api /storefront-api
USER 65532:65532
```

- The unit tests run *inside* the build: if they fail, no image exists.
- `-trimpath`, `-buildid=` and `-buildvcs=false` make the binary more reproducible (no local paths or random IDs inside).
- `VERSION` and `COMMIT` are baked in, so `/version` tells you which commit is running.

The deployment files reference the image only by digest ([`deploy/prod/kustomization.yaml`](../deploy/prod/kustomization.yaml)):

```yaml
images:
  - name: ghcr.io/sufyanahmadkamboh/storefront-api
    digest: sha256:...
```

## Try it

```bash
source scripts/lib.sh
# list what is stored in the registry: image tags plus .sig/.att artifacts
tb crane ls ghcr.io/sufyanahmadkamboh/storefront-api
# resolve a tag to its digest
tb crane digest ghcr.io/sufyanahmadkamboh/storefront-api:<a sha-... tag from the list>
# look at the manifest (layers and their digests)
tb crane manifest ghcr.io/sufyanahmadkamboh/storefront-api:<tag> | tb jq .
```

## Common mistakes

- Deploying `:latest` or any tag in production. The content behind a tag can change without any change in your git repository.
- Using a "full" base image (with shell, package manager, compilers) for a program that needs none of it.
- Pinning only the final base image, not the build image: a moved build image can inject code into your binary.

## Check yourself

1. What is the difference between a tag and a digest?
2. Why does this project pin `golang` and `distroless` by digest even though they come from official publishers?
3. Where does cosign store an image's signature?

### Answers

<details><summary>Answers</summary>

1. A tag is a movable name; a digest is the SHA-256 hash of the image manifest and therefore identifies exactly one content.
2. Tags of official images are updated regularly (and could be moved maliciously). A digest guarantees the build always uses the exact same base content; Dependabot proposes updates as reviewed pull requests.
3. In the same registry repository, as a separate artifact linked to the image digest (in this project the classic `sha256-<digest>.sig` tag; attestations in `sha256-<digest>.att`).

</details>
