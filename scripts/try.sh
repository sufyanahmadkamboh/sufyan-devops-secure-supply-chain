#!/usr/bin/env bash
# Hands-on exercises for the local lab (start it first with scripts/platform-up.sh).
#   scripts/try.sh <exercise>
#
#   status          what runs where: platform pods, policies, the release in prod
#   verify          check the release signature yourself, like the cluster does
#   wrong-identity  the same check, expecting a different workflow: it must fail
#   trusted         start the signed release as a pod in prod (admitted, pinned to its digest)
#   foreign         start a Docker Hub image in prod (refused: allowed-images)
#   unsigned        build your own image under the trusted name, load it into the cluster (refused: no signature)
#   privileged      start the trusted image as a privileged pod (refused: Pod Security)
#   sandbox         start an unsigned image in the audit namespace (allowed, but reported)
#   scan            run an old nginx in the sandbox and wait for Trivy Operator's report
#   alerts          show Prometheus alerts
#   dashboard       open Grafana on http://localhost:3000 (Ctrl+C to stop)
#   clean           delete the pods these exercises created
# shellcheck source=lib.sh
source "$(dirname "$0")/lib.sh"
cd "$ROOT" || exit 1

IMAGE=ghcr.io/sufyanahmadkamboh/storefront-api
ID="https://github.com/sufyanahmadkamboh/sufyan-devops-secure-supply-chain/.github/workflows/release.yaml@refs/heads/main"
ISSUER=https://token.actions.githubusercontent.com
DIGEST="$(grep -oE 'sha256:[a-f0-9]{64}' deploy/prod/kustomization.yaml)"
[[ -f "$STATE/kubeconfig" ]] || die "no lab cluster: run scripts/platform-up.sh first"

# A pod that satisfies Pod Security "restricted", so only the image (or privileged) decides the outcome.
pod() {  # name namespace image [privileged]
  local priv="${4:-false}"
  cat <<EOF
apiVersion: v1
kind: Pod
metadata: {name: $1, namespace: $2, labels: {exercise: "true"}}
spec:
  automountServiceAccountToken: false
  securityContext: {runAsNonRoot: true, runAsUser: 65532, seccompProfile: {type: RuntimeDefault}}
  containers:
    - name: app
      image: $3
      imagePullPolicy: IfNotPresent
      securityContext: {allowPrivilegeEscalation: $priv, privileged: $priv, readOnlyRootFilesystem: true, capabilities: {drop: [ALL]}}
      resources: {limits: {cpu: 100m, memory: 32Mi}}
EOF
}

# Try to create a pod and report what the cluster said, with the time it took.
attempt() {  # name namespace image [privileged]
  local start out
  start=$(date +%s%N)
  k -n "$2" delete pod "$1" --ignore-not-found --wait=false >/dev/null
  if out="$(pod "$@" | k apply -f - 2>&1)"; then
    printf '\033[1;32mADMITTED\033[0m in %s ms: %s\n' "$(( ($(date +%s%N) - start) / 1000000 ))" "$out"
    return 0
  fi
  printf '\033[1;31mREFUSED\033[0m in %s ms\n' "$(( ($(date +%s%N) - start) / 1000000 ))"
  echo "$out" | grep -oE 'denied the request: .*|violates PodSecurity .*' | head -n1 | cut -c1-220
}

case "${1:-}" in
  status)
    log "Platform"
    k get pods -A --no-headers | awk '$1 ~ /kyverno|argocd|trivy|monitoring|prod|sandbox/ {print $1, $2, $4}' | column -t
    log "Admission policies (prod: Deny, sandbox: Audit)"
    k get ivpol,vpol --no-headers | awk '{print $1}'
    log "The release Argo CD deployed to prod"
    k -n argocd get application storefront-api -o jsonpath='{.status.sync.status} / {.status.health.status}{"\n"}'
    k -n prod get pods -o jsonpath='{range .items[*]}{.metadata.name}  {.spec.containers[0].image}{"\n"}{end}'
    ;;
  verify)
    log "Is $IMAGE@${DIGEST:0:19}… signed by release.yaml on main?"
    tb cosign verify --certificate-identity "$ID" --certificate-oidc-issuer "$ISSUER" "$IMAGE@$DIGEST" 2>&1 >/dev/null | grep -v '^$'
    tb cosign verify --certificate-identity "$ID" --certificate-oidc-issuer "$ISSUER" "$IMAGE@$DIGEST" 2>/dev/null \
      | tb jq -r '.[0].optional | "built from commit \(.githubWorkflowSha) by \(.githubWorkflowName) (\(.githubWorkflowTrigger))"'
    for t in slsaprovenance1 vuln cyclonedx; do
      tb cosign verify-attestation --type "$t" --certificate-identity "$ID" --certificate-oidc-issuer "$ISSUER" \
        "$IMAGE@$DIGEST" >/dev/null 2>&1 && ok "signed $t attestation"
    done
    ;;
  wrong-identity)
    log "Same image, but expecting a different workflow (ci.yaml) as the signer"
    if tb cosign verify --certificate-identity "${ID/release.yaml/ci.yaml}" --certificate-oidc-issuer "$ISSUER" "$IMAGE@$DIGEST" >/dev/null 2>"$STATE/err"; then
      die "verification unexpectedly succeeded"
    fi
    printf '\033[1;31mFAILED\033[0m as expected: %s\n' "$(grep -oE 'none of the expected identities matched.*' "$STATE/err" | cut -c1-160)"
    ;;
  trusted)
    attempt try-trusted prod "$IMAGE@$DIGEST"
    ;;
  foreign)
    attempt try-foreign prod docker.io/library/nginx:1.29
    ;;
  unsigned)
    log "Building your own image and calling it $IMAGE:local (what a stolen token would allow)"
    docker build -q -t "$IMAGE:local" app >/dev/null
    "$KIND" load docker-image "$IMAGE:local" --name "$CLUSTER" >/dev/null 2>&1
    attempt try-unsigned prod "$IMAGE:local"
    ;;
  privileged)
    attempt try-privileged prod "$IMAGE@$DIGEST" true
    ;;
  sandbox)
    attempt try-sandbox sandbox docker.io/library/nginx:1.29
    log "Waiting for the PolicyReport (audit mode reports instead of blocking)"
    reported() { k -n sandbox get policyreports -o json | tb jq -e '[.items[] | select(.scope.name=="try-sandbox") | .results[]? | select(.result=="fail")] | length > 0' >/dev/null; }
    wait_for 180 reported >/dev/null || die "no PolicyReport yet, run the exercise again in a minute"
    k -n sandbox get policyreports -o json \
      | tb jq -r '.items[] | select(.scope.name=="try-sandbox") | .results[]? | select(.result=="fail") | "would be refused in prod: \(.policy)"'
    ;;
  scan)
    attempt try-scan sandbox docker.io/library/nginx:1.21.0
    log "Waiting for Trivy Operator to scan it (a few minutes the first time)"
    scanned() { k -n sandbox get vulnerabilityreports -o json | tb jq -e '[.items[] | select(.report.artifact.tag=="1.21.0")] | length > 0' >/dev/null; }
    wait_for 900 scanned >/dev/null || die "no VulnerabilityReport yet, run the exercise again later"
    k -n sandbox get vulnerabilityreports -o json \
      | tb jq -r '.items[] | select(.report.artifact.tag=="1.21.0") | .report | "\(.artifact.repository):\(.artifact.tag)  CRITICAL \(.summary.criticalCount)  HIGH \(.summary.highCount)"'
    ;;
  alerts)
    k -n monitoring exec deploy/prometheus -- wget -qO- http://localhost:9090/api/v1/alerts \
      | tb jq -r '.data.alerts[] | "\(.state)\t\(.labels.alertname)\t\(.annotations.summary)"'
    ;;
  dashboard)
    log "Grafana: http://localhost:3000 (Ctrl+C to stop)"
    docker run --rm -it --network kind -p 3000:3000 -v "$ROOT_NATIVE:/work" -w /work -e KUBECONFIG=/work/.lab/kubeconfig \
      "$TOOLBOX_IMAGE" kubectl -n monitoring port-forward --address 0.0.0.0 svc/grafana 3000
    ;;
  clean)
    k delete pods -A -l exercise=true --ignore-not-found
    ;;
  *)
    sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'
    exit 1
    ;;
esac
