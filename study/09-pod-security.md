# 9. Pod security: a trusted image can still be run dangerously

## What is it?

A signature proves *what* runs. It says nothing about *how* it runs. The same signed image started as a **privileged** container, as **root**, or with the host's file system mounted can take over the node it runs on.

Kubernetes defines three **Pod Security Standards**:

| Level | Meaning |
|---|---|
| `privileged` | no restrictions |
| `baseline` | blocks the obvious escalations (privileged, host namespaces, hostPath...) |
| `restricted` | baseline plus: non-root, no privilege escalation, all capabilities dropped, seccomp profile set |

**Pod Security Admission (PSA)** is built into Kubernetes and enforces one level per namespace through a label such as `pod-security.kubernetes.io/enforce: restricted`.

## Why this project uses it

Two layers, on purpose:

1. **PSA `restricted`** on the prod namespace: built in, cannot be switched off by deleting a Kyverno policy.
2. **The Kyverno policy `restricted-pods`**: the same ideas, plus rules PSA does not have (read-only root file system, CPU and memory limits), with clear messages, PolicyReports and an audit version for the sandbox.

**Alternatives:** PSA alone; OPA Gatekeeper's pod security library; Kyverno's own `podSecurity` subrule in the older ClusterPolicy API.

## How it works

The settings and what each one blocks:

| Setting | Blocks |
|---|---|
| `runAsNonRoot: true` | running as UID 0 (root inside the container is a short step from root on the node) |
| `allowPrivilegeEscalation: false` | gaining privileges with setuid binaries |
| `privileged: false` | full access to the host's devices and kernel |
| `capabilities: {drop: [ALL]}` | special kernel powers (raw network, changing file owners...) |
| `readOnlyRootFilesystem: true` | dropping and running tools inside the container |
| `seccompProfile: RuntimeDefault` | rarely needed, dangerous system calls (PSA restricted demands it) |
| no `hostNetwork`, `hostPID`, `hostPath` | reaching into the node itself |
| CPU and memory limits | one pod starving the node |

## Where it is integrated

The prod namespace, [`deploy/prod/namespace.yaml`](../deploy/prod/namespace.yaml):

```yaml
  labels:
    supply-chain.sufyan.dev/enforce: "true"
    pod-security.kubernetes.io/enforce: restricted
```

The Kyverno policy, [`policies/base/pod-security.yaml`](../policies/base/pod-security.yaml) (excerpt):

```yaml
    - expression: >-
        !has(object.spec.volumes) || object.spec.volumes.all(v, !has(v.hostPath))
      message: hostPath volumes are not allowed
    - expression: >-
        variables.containers.all(c, has(c.resources) && has(c.resources.limits)
          && "memory" in c.resources.limits && "cpu" in c.resources.limits)
      message: containers must set CPU and memory limits
```

The application follows all of it, [`deploy/base/storefront-api.yaml`](../deploy/base/storefront-api.yaml):

```yaml
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        runAsGroup: 65532
        seccompProfile: {type: RuntimeDefault}
      containers:
        - name: app
          ...
          resources:
            requests: {cpu: 20m, memory: 16Mi}
            limits: {cpu: 200m, memory: 64Mi}
          securityContext:
            runAsNonRoot: true
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities: {drop: [ALL]}
```

The same file also turns off the service account token (`automountServiceAccountToken: false`, the app never calls the Kubernetes API) and adds a NetworkPolicy with `egress: []`: the app may receive HTTP but open no outbound connections at all.

The e2e test starts the **trusted, signed image as a privileged container** and expects it to be refused (chapter 13).

## Try it

```bash
source scripts/lib.sh
# PSA warns or refuses before Kyverno even sees the request:
k -n prod run root-shell --image=docker.io/library/busybox:1.37 -- sleep 3600
# offline: the policy tests contain privileged, root, hostPath and no-limits pods
tb kyverno test policies/tests
grep -n "metadata:" policies/tests/resources.yaml   # privileged-pod, root-pod, hostpath-pod, no-limits-pod...
```

## Common mistakes

- Thinking image signing makes pod settings irrelevant.
- Setting `runAsNonRoot: true` with an image whose user is root: the pod fails to start (`CreateContainerConfigError`). The distroless `nonroot` base uses UID 65532, which matches `runAsUser` here.
- Forgetting `seccompProfile: RuntimeDefault`: PSA `restricted` refuses the pod even when everything else is right.
- `readOnlyRootFilesystem: true` for an app that writes temp files: mount an `emptyDir` at `/tmp` instead of turning the setting off.

## Check yourself

1. Why keep PSA if Kyverno already checks the same things?
2. Which pod setting is needed by PSA `restricted` but easy to forget?
3. Why does the app's NetworkPolicy have `egress: []`?

### Answers

<details><summary>Answers</summary>

1. Defence in depth: PSA is built into the API server and keeps working if the Kyverno policies are deleted or the webhook is down with `failurePolicy: Ignore`. Kyverno adds the rules PSA lacks (read-only root, limits) and reporting.
2. `seccompProfile: {type: RuntimeDefault}` (at pod or container level).
3. The app needs no outbound connections. If it were compromised, it could not download tools or send data out.

</details>
