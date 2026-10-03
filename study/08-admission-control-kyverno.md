# 8. Admission control with Kyverno

## What is it?

When anything asks the Kubernetes API to create or change an object (a Pod, a Deployment...), the request passes through **admission controllers** before it is stored. **Admission webhooks** let external programs take part: a *mutating* webhook can change the object, a *validating* webhook can accept or refuse it.

**Kyverno** is a policy engine that runs as such a webhook. You write policies as Kubernetes resources; Kyverno evaluates them on every matching request.

## Why this project uses it

It is the **pharmacist** of chapter 0: the single place where every Pod is checked, no matter who or what created it (kubectl, Argo CD, a CronJob, an attacker with a stolen kubeconfig of a normal user).

**Alternatives:** Sigstore **policy-controller** (only image verification), **OPA Gatekeeper** (Rego language; image verification needs extra work), **Connaisseur**, Kubernetes **ValidatingAdmissionPolicy** (built in, CEL, but no image verification).

## How it works

### Policy types used here (Kyverno 1.19)

| Kind | Language | Used for |
|---|---|---|
| `ImageValidatingPolicy` | CEL + Sigstore verification | signatures and attestations of images |
| `ValidatingPolicy` | CEL | allowed registries, digest pinning, pod security |

The older `ClusterPolicy` kind is deprecated in 1.19, so this project uses only the new CEL-based kinds.

### CEL in two minutes
**CEL** (Common Expression Language) is a small, safe expression language, also used by Kubernetes itself. Examples from this project:
- `object.spec.containers` — the containers of the Pod being checked
- `images.all(i, i.startsWith("ghcr.io/..."))` — true if *every* image matches
- `has(c.securityContext)` — does the field exist?
- `variables.images` — a value defined once in the policy's `variables:` list

### mutateDigest and verifyDigest
`mutateDigest: true` rewrites `image: ...:sha-abc` to `image: ...:sha-abc@sha256:...` — the exact content that was verified. Even if the tag moves a second later, the Pod runs what was checked.

### Deny vs Audit
`validationActions: [Deny]` refuses violating requests. `[Audit]` lets them through and records the result in a **PolicyReport**. This project uses the same rules in both modes (prod: Deny, sandbox: Audit) via Kustomize.

### Policy tests
`kyverno test` evaluates policies against example resources offline, with expected results, so a wrong rule is caught in CI before it reaches a cluster.

## Where it is integrated

Three policies in [`policies/base/`](../policies/base/):

1. [`verify-images.yaml`](../policies/base/verify-images.yaml) — signature, provenance, scan and SBOM checks (chapters 6 and 7):

```yaml
  matchImageReferences:
    - glob: "ghcr.io/sufyanahmadkamboh/storefront-api*"
  ...
  validationConfigurations:
    mutateDigest: true
    verifyDigest: true
    required: true
  validations:
    - expression: >-
        images.containers.map(image, verifyImageSignatures(image, [attestors["release-workflow"]])).all(n, n > 0)
      message: image is not signed by the release workflow of sufyan-devops-secure-supply-chain (main branch)
```

2. [`allowed-images.yaml`](../policies/base/allowed-images.yaml) — only this repository's images, and digests in workload specs:

```yaml
    - expression: >-
        variables.images.all(i, i.startsWith("ghcr.io/sufyanahmadkamboh/storefront-api:")
          || i.startsWith("ghcr.io/sufyanahmadkamboh/storefront-api@"))
    ...
    - expression: "object.kind == 'Pod' || variables.images.all(i, i.matches('@sha256:[a-f0-9]{64}$'))"
      message: workloads must reference images by digest (image@sha256:...), not by a movable tag
```

   Note the `:` and `@` in the prefix check: without them, a look-alike repository such as `storefront-api-evil` would pass.

3. [`pod-security.yaml`](../policies/base/pod-security.yaml) — chapter 9.

Both modes come from overlays: [`policies/prod/kustomization.yaml`](../policies/prod/kustomization.yaml) uses the base unchanged (Deny), and [`policies/sandbox/kustomization.yaml`](../policies/sandbox/kustomization.yaml) patches every policy:

```yaml
nameSuffix: -audit
patches:
  - target:
      group: policies.kyverno.io
    patch: |-
      - op: replace
        path: /spec/validationActions
        value: [Audit]
      - op: replace
        path: /spec/matchConstraints/namespaceSelector/matchLabels
        value:
          supply-chain.sufyan.dev/audit: "true"
```

`allowed-images` also matches Deployments, StatefulSets, DaemonSets and ReplicaSets directly (with `autogen` switched off), so a tag-only Deployment is refused at `kubectl apply` time. The image signature policy matches Pods, the place where an image actually starts.

Namespaces opt in with labels: `supply-chain.sufyan.dev/enforce: "true"` (prod, [`deploy/prod/namespace.yaml`](../deploy/prod/namespace.yaml)) or `supply-chain.sufyan.dev/audit: "true"` (sandbox).

Offline tests: [`policies/tests/kyverno-test.yaml`](../policies/tests/kyverno-test.yaml) runs the two ValidatingPolicies against [`policies/tests/resources.yaml`](../policies/tests/resources.yaml) (a good Deployment, a tag-only one, a foreign registry, a look-alike repository, privileged/root/hostPath/no-limits pods). Signature checks need a registry and Sigstore, so they are tested end to end instead (chapter 13).

## Try it

```bash
scripts/platform-up.sh
source scripts/lib.sh
k get ivpol,vpol
tb kyverno test policies/tests
# a foreign image with a SAFE pod spec, so only Kyverno can object (same shape as the e2e test):
cat <<'EOF' | tb kubectl apply -f -
apiVersion: v1
kind: Pod
metadata: {name: try-foreign, namespace: prod}
spec:
  securityContext: {seccompProfile: {type: RuntimeDefault}}
  containers:
    - name: app
      image: docker.io/library/nginx:1.29
      securityContext:
        runAsNonRoot: true
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities: {drop: [ALL]}
      resources: {limits: {cpu: 100m, memory: 32Mi}}
EOF
# -> denied: "only ghcr.io/sufyanahmadkamboh/storefront-api images may run here, got: docker.io/library/nginx:1.29"

# the sandbox has no enforcing label: a plain pod is allowed, and reported
k -n sandbox run nginx --image=docker.io/library/nginx:1.29
k -n sandbox get policyreports -o wide
```

Why the long manifest? The prod namespace also has the built-in Kubernetes Pod Security label `restricted` (chapter 9). A plain `kubectl run` there would be refused by that check first, and you would not see Kyverno's message.

## Common mistakes

- Matching images with a glob like `.../storefront-api*` in a registry allowlist: it also matches `storefront-api-evil`.
- Only checking Pods created with kubectl. Deployments create Pods through ReplicaSets, so a refused Pod shows up as a `FailedCreate` event on the ReplicaSet, not as an error on `kubectl apply`.
- Forgetting the Kyverno webhook can be unavailable at start-up; `helm --wait` returns before it serves requests (the platform script retries).
- Writing `extractPayload(...).result` instead of `.predicate.result`.

## Check yourself

1. Why does `allowed-images` check `storefront-api:` and `storefront-api@` instead of just `storefront-api`?
2. What does `mutateDigest: true` protect against?
3. If a Deployment uses an unsigned image, does `kubectl apply` of the Deployment fail?

### Answers

<details><summary>Answers</summary>

1. A plain prefix would also match a look-alike repository such as `ghcr.io/sufyanahmadkamboh/storefront-api-evil`. The tests include exactly that case.
2. Against the tag being moved after verification: the Pod is rewritten to the digest that was verified, so it runs exactly what was checked.
3. Not necessarily: the image signature is verified on Pods. The Deployment and ReplicaSet are created, but the ReplicaSet's Pod creation is refused (`FailedCreate` events). In prod, `allowed-images` already refuses Deployments that use tags or foreign registries.

</details>
