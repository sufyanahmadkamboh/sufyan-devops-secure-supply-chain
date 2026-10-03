#!/usr/bin/env bash
# Builds the whole platform on a local kind cluster:
#   Kyverno + policies (prod: enforce, sandbox: audit) · Argo CD + the storefront-api Application
#   Trivy Operator (re-scans running images) · Prometheus + Grafana with alert rules and dashboard
# Environment: ARGO_REVISION (git branch/commit Argo CD follows, default main)
# shellcheck source=lib.sh
source "$(dirname "$0")/lib.sh"
cd "$ROOT" || exit 1

KYVERNO_CHART=3.9.1          # Kyverno v1.19.1
TRIVY_OPERATOR_CHART=0.36.0  # Trivy Operator v0.34.0
ARGOCD_VERSION=v3.5.3
ARGO_REVISION="${ARGO_REVISION:-main}"
mkdir -p "$STATE"

if ! docker image inspect "$TOOLBOX_IMAGE" >/dev/null 2>&1; then
  log "Building the toolbox image"
  docker build -q -t "$TOOLBOX_IMAGE" tools/toolbox >/dev/null
fi

if ! "$KIND" get clusters 2>/dev/null | grep -qx "$CLUSTER"; then
  log "Creating kind cluster $CLUSTER"
  "$KIND" create cluster --config platform/kind.yaml --name "$CLUSTER" --wait 180s
fi
"$KIND" get kubeconfig --internal --name "$CLUSTER" > "$STATE/kubeconfig"

log "Kyverno (chart $KYVERNO_CHART)"
tb bash -c "helm repo add kyverno https://kyverno.github.io/kyverno/ >/dev/null 2>&1; helm repo update kyverno >/dev/null
  helm upgrade --install kyverno kyverno/kyverno --version $KYVERNO_CHART -n kyverno --create-namespace \
    --set admissionController.replicas=1 --wait --timeout 8m >/dev/null"

log "Admission policies (prod: Deny, sandbox: Audit)"
# Helm reports Kyverno ready before its webhook serves requests: retry until the policies are accepted.
apply_policies() { tb bash -c 'kubectl kustomize policies/prod | kubectl apply -f - && kubectl kustomize policies/sandbox | kubectl apply -f -'; }
wait_for 180 apply_policies >/dev/null || { apply_policies; die "Kyverno did not accept the policies"; }
policies_ready() { [[ "$(k get vpol,ivpol -o jsonpath='{range .items[*]}{.status.conditionStatus.ready}{"\n"}{end}' | grep -c true)" == 6 ]]; }
wait_for 180 policies_ready >/dev/null || die "policies not ready"

log "Namespaces"
tb bash -c 'kubectl apply -f deploy/prod/namespace.yaml
  kubectl create namespace sandbox --dry-run=client -o yaml | kubectl apply -f -
  kubectl label namespace sandbox supply-chain.sufyan.dev/audit=true --overwrite' >/dev/null

log "Argo CD $ARGOCD_VERSION"
tb bash -c "kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f - >/dev/null
  kubectl apply --server-side --force-conflicts -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/$ARGOCD_VERSION/manifests/install.yaml >/dev/null
  kubectl -n argocd rollout status deploy/argocd-repo-server --timeout=5m >/dev/null
  kubectl -n argocd rollout status statefulset/argocd-application-controller --timeout=5m >/dev/null"

log "Trivy Operator (chart $TRIVY_OPERATOR_CHART), scanning prod and sandbox"
tb bash -c "helm repo add aqua https://aquasecurity.github.io/helm-charts/ >/dev/null 2>&1; helm repo update aqua >/dev/null
  helm upgrade --install trivy-operator aqua/trivy-operator --version $TRIVY_OPERATOR_CHART -n trivy-system --create-namespace \
    --set targetNamespaces='prod\,sandbox' \
    --set operator.scanJobsConcurrentLimit=2 \
    --set operator.configAuditScannerEnabled=false --set operator.rbacAssessmentScannerEnabled=false \
    --set operator.infraAssessmentScannerEnabled=false --set operator.clusterComplianceEnabled=false \
    --set operator.exposedSecretScannerEnabled=false \
    --set trivy.severity='CRITICAL\,HIGH' \
    --wait --timeout 8m >/dev/null"

log "Prometheus + Grafana"
tb bash -c 'kubectl apply -f platform/monitoring/prometheus.yaml >/dev/null
  kubectl -n monitoring create configmap prometheus-rules --from-file=rules.yaml=platform/monitoring/rules.yaml --dry-run=client -o yaml | kubectl apply -f - >/dev/null
  kubectl -n monitoring create configmap grafana-dashboards --from-file=supply-chain.json=platform/monitoring/dashboard.json --dry-run=client -o yaml | kubectl apply -f - >/dev/null
  kubectl apply -f platform/monitoring/grafana.yaml >/dev/null
  kubectl -n monitoring rollout status deploy/prometheus --timeout=3m >/dev/null
  kubectl -n monitoring rollout status deploy/grafana --timeout=3m >/dev/null'

log "Argo CD Application (follows: $ARGO_REVISION)"
sed "s|targetRevision: main|targetRevision: $ARGO_REVISION|" platform/argocd/application.yaml | tb kubectl apply -f - >/dev/null
ok "Platform ready"
