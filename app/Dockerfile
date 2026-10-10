# Base images are pinned by digest: a tag can be moved to different content, a digest cannot.
FROM golang:1.27.1-trixie@sha256:8f58fd67ea075142d947a60e0caa4317746a55118d312f027793d382c7741734 AS build
WORKDIR /src
COPY go.mod ./
COPY *.go ./
ARG VERSION=dev
ARG COMMIT=unknown
# Static, reproducible binary: no cgo, no local paths, no build id.
RUN go test ./... \
 && CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -trimpath -buildvcs=false \
      -ldflags="-s -w -buildid= -X main.version=${VERSION} -X main.commit=${COMMIT}" -o /out/storefront-api .

# No shell, no package manager, runs as uid 65532.
FROM gcr.io/distroless/static-debian13:nonroot@sha256:e2e927ec666bae08560abb3c55d0659eceabb657f56b6782ab500a9fc7f555e3
COPY --from=build /out/storefront-api /storefront-api
USER 65532:65532
EXPOSE 8080
ENTRYPOINT ["/storefront-api"]
