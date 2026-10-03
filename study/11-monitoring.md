# 11. Monitoring: Prometheus alerts and a Grafana dashboard

## What is it?

- **Prometheus** collects numeric **metrics** from programs over HTTP (it *scrapes* a `/metrics` page every few seconds), stores them as time series, and evaluates **alert rules** written in **PromQL**.
- **Grafana** draws dashboards from those metrics.
- **promtool** is Prometheus's command-line tool. `promtool test rules` runs **unit tests for alerts**: given fake input series, which alerts must fire, with which labels and text.

## Why this project uses it

A blocked attack that nobody notices is only half a defence. Somebody pushed an unsigned image, or committed a bad digest: the team must know *now*. And a running image that becomes vulnerable must page someone, not wait for the next release.

**Alternatives:** kube-prometheus-stack (Prometheus Operator, Alertmanager, many default rules; heavier), Datadog / Grafana Cloud / New Relic agents, Kyverno's own PolicyReports viewed with Policy Reporter.

## How it works

Three sources are scraped ([`platform/monitoring/prometheus.yaml`](../platform/monitoring/prometheus.yaml)):

| Job | Metrics used |
|---|---|
| `kyverno-admission` | `kyverno_admission_requests_total` (label `request_allowed`), `kyverno_image_validating_policy_results_total`, `kyverno_admission_review_duration_seconds` |
| `kyverno-reports` | report controller health |
| `trivy-operator` | `trivy_image_vulnerabilities` (labels `namespace`, `image_repository`, `severity`...) |

Some PromQL you need:
- `increase(counter[10m])` — how much a counter grew in 10 minutes.
- `sum by (label) (...)` — add series together, keep one series per value of `label`.
- `absent(expr)` — returns 1 when the expression has no result (used to detect a missing target).
- `for: 5m` — the condition must hold for 5 minutes before the alert fires (avoids noise).

## Where it is integrated

The alert rules, [`platform/monitoring/rules.yaml`](../platform/monitoring/rules.yaml):

```yaml
      - alert: UntrustedWorkloadBlocked
        expr: >-
          sum by (resource_namespace, resource_kind) (
            (
              (kyverno_admission_requests_total{request_allowed="false", resource_namespace="prod"}
                unless kyverno_admission_requests_total{request_allowed="false", resource_namespace="prod"} offset 10m) * 1
              and on () (time() - process_start_time_seconds{job="prometheus"} > 600)
            )
            or
            increase(kyverno_admission_requests_total{request_allowed="false", resource_namespace="prod"}[10m])
          ) > 0
        labels:
          severity: critical
```

Read it from the bottom up:
- `increase(...[10m])` is the main part: how many refusals happened in the last 10 minutes.
- The first part covers a gap found while testing this project. Kyverno creates a counter only when the first refusal of a kind happens, and the counter starts at that value (for example 3), with no earlier 0. `increase()` needs two samples to see growth, so those first refusals would be invisible. `X unless X offset 10m` keeps only counters that did not exist 10 minutes ago, and counts them with their full value. `* 1` drops the metric name so `or` can line them up with `increase()`'s results.
- There is no `request_webhook` filter on purpose. `verify-release-images` also rewrites the image to its digest, so Kyverno runs it in the *mutating* phase, and a missing or wrong signature is refused there (`request_webhook="MutatingWebhookConfiguration"`). `allowed-images` and `restricted-pods` refuse in the *validating* phase. A request is refused in one phase only, so summing both counts each refusal once. An earlier version counted only the validating phase and missed exactly the unsigned and imposter images; the local dashboard demo showed 10 refusals where 19 had happened.
- `and on () (time() - process_start_time_seconds… > 600)` switches that first part off for Prometheus' first 10 minutes. Its storage is not persistent here, so after a restart every counter "did not exist 10 minutes ago", and the alert would fire for old refusals.

```yaml
      - alert: AdmissionControllerDown
        expr: absent(up{job="kyverno-admission"} == 1)
        for: 5m
```

`RunningImageHasCriticalVulnerabilities` was shown in chapter 5.

Why no `for:` on `UntrustedWorkloadBlocked`? In a healthy pipeline nothing is ever refused in prod, so even one refusal is worth a page.

The tests, [`tests/prometheus/rules.test.yaml`](../tests/prometheus/rules.test.yaml): refusals in prod make the alert fire; refusals in sandbox and allowed requests do not:

```yaml
      - series: 'kyverno_admission_requests_total{request_allowed="false",request_webhook="ValidatingWebhookConfiguration",resource_kind="Pod",resource_namespace="prod",resource_request_operation="create"}'
        values: "0 0 1 2 2"
      - series: 'kyverno_admission_requests_total{request_allowed="false",request_webhook="ValidatingWebhookConfiguration",resource_kind="Pod",resource_namespace="sandbox",resource_request_operation="create"}'
        values: "0 5 10 15 20"
```

They run in CI ([`.github/workflows/ci.yaml`](../.github/workflows/ci.yaml)):

```bash
docker run --rm -v "$PWD:/w" -w /w/tests/prometheus --entrypoint promtool prom/prometheus:v3.15.0 test rules rules.test.yaml
```

A detail learned the hard way: the Trivy Operator Service is **headless** (no cluster IP), so its DNS name returns the pod IP directly and Prometheus must use the container port 8080:

```yaml
      - job_name: trivy-operator
        static_configs:
          # headless service: DNS returns the pod IP, so use the container port
          - targets: ["trivy-operator.trivy-system.svc:8080"]
```

The dashboard, [`platform/monitoring/dashboard.json`](../platform/monitoring/dashboard.json), "Software supply chain: what runs and why", answers three questions top to bottom: *Is production running only trusted code?* (blocked in prod, signature checks, running images with CRITICAL CVEs, firing alerts), *what was refused and where*, and *is the admission controller healthy and fast* (p95 latency of admission reviews and of image policy execution).

## Try it

```bash
# alert unit tests, no cluster needed
docker run --rm -v "$PWD:/w" -w /w/tests/prometheus --entrypoint promtool prom/prometheus:v3.15.0 test rules rules.test.yaml

# with the lab running: which alerts fire?
source scripts/lib.sh
k -n monitoring exec deploy/prometheus -- wget -qO- 'http://localhost:9090/api/v1/alerts' | tb jq '.data.alerts[] | {alert: .labels.alertname, state}'

# open Grafana in your browser (anonymous viewer) at http://localhost:3000
docker run --rm -it --network kind -p 3000:3000 -v "$ROOT_NATIVE/.lab:/lab" -e KUBECONFIG=/lab/kubeconfig \
  "$TOOLBOX_IMAGE" kubectl -n monitoring port-forward --address 0.0.0.0 svc/grafana 3000:3000
```

## Common mistakes

- Alerting on `kyverno_admission_requests_total` without `increase()`: a counter never goes down, so the alert would fire forever after the first refusal.
- Filtering a "refused" counter by webhook phase without checking which phase each policy refuses in.
- Relying on `increase()` alone for rare events: a counter that is created already above 0 shows no increase, so the very first refusals are missed. The promtool tests include exactly this case (`values: "_ _ 3 3 3"`, where `_` means "no sample yet").
- Counting refusals in every namespace: the sandbox and test namespaces would page people all day.
- Alert rules without tests: a typo in a label name means the alert silently never fires.
- `absent()` on the wrong job name: the "controller down" alert fires constantly, or never.

## Check yourself

1. Why does `UntrustedWorkloadBlocked` use `increase(...[10m])` instead of the raw counter?
2. What does the promtool test prove for the sandbox series?
3. Why does Prometheus scrape Trivy Operator on port 8080 instead of the Service port?

### Answers

<details><summary>Answers</summary>

1. The counter only ever grows. `increase` over 10 minutes is above 0 only while refusals are recent, so the alert also resolves on its own.
2. That refusals in the sandbox (audit namespace) do not trigger the prod alert, even when they are frequent.
3. The Service is headless: its DNS name resolves straight to the pod IP, where only the container port (8080) is listening. There is no Service port translation.

</details>
