# 10. GitOps with Argo CD

## What is it?

**GitOps** means: the desired state of the cluster lives in a git repository, and a controller inside the cluster keeps the cluster equal to git. Nobody runs `kubectl apply` against production by hand; changes are commits, reviewed and recorded.

**Argo CD** is the most widely used GitOps controller. You describe an **Application** (which repo, which path, which branch, which namespace), and Argo CD **syncs** it: it renders the manifests (here with Kustomize) and applies the difference.

## Why this project uses it

- Every production change is a git commit: who, when, what, and an easy rollback (`git revert`).
- The release pipeline does not need cluster credentials. It only commits a digest; Argo CD pulls from inside.
- It is a realistic attack path to test: **someone who can write to the deploy folder** can make Argo CD apply anything.

The key design point: **Argo CD is not trusted with security decisions.** Whatever it applies still goes through Kyverno admission. A malicious commit is synced, and its pods are refused.

**Alternatives:** Flux CD (also CNCF graduated, more "toolkit" style), push-based deploys from CI with `kubectl`/Helm (the CI then needs cluster credentials), Rancher Fleet.

## How it works

1. Argo CD polls the repository (about every 3 minutes by default) or is told to refresh.
2. It renders `deploy/prod` with Kustomize and compares it with the live objects: **Synced** or **OutOfSync**.
3. With `automated` sync, it applies the difference. `prune: true` deletes objects removed from git; `selfHeal: true` undoes manual changes in the cluster.
4. It reports **health** (are the Deployments rolled out?) separately from sync status.

### Why old pods keep serving during an attack
The Deployment uses `maxUnavailable: 0, maxSurge: 1`. Kubernetes first creates a new pod and removes an old one only when the new one is ready. If Kyverno refuses the new pod, it never exists, so **no old pod is removed**. Production keeps serving the trusted version while the rollout is stuck.

## Where it is integrated

[`platform/argocd/application.yaml`](../platform/argocd/application.yaml):

```yaml
spec:
  project: default
  source:
    repoURL: https://github.com/sufyanahmadkamboh/sufyan-devops-secure-supply-chain.git
    targetRevision: main
    path: deploy/prod
  destination:
    server: https://kubernetes.default.svc
    namespace: prod
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

What it deploys, [`deploy/prod/kustomization.yaml`](../deploy/prod/kustomization.yaml): the base plus one exact digest, written by the release workflow's `promote` job:

```yaml
images:
  - name: ghcr.io/sufyanahmadkamboh/storefront-api
    digest: sha256:0000000000000000000000000000000000000000000000000000000000000000
```

(The all-zero value is the placeholder in the repository until the first release is promoted.)

The rollout strategy, [`deploy/base/storefront-api.yaml`](../deploy/base/storefront-api.yaml):

```yaml
  strategy:
    type: RollingUpdate
    rollingUpdate: {maxUnavailable: 0, maxSurge: 1}
```

[`scripts/platform-up.sh`](../scripts/platform-up.sh) installs Argo CD and lets the e2e test point the Application at a temporary branch (`ARGO_REVISION`), so the attack test never touches `main`:

```bash
sed "s|targetRevision: main|targetRevision: $ARGO_REVISION|" platform/argocd/application.yaml | tb kubectl apply -f - >/dev/null
```

## Try it

```bash
source scripts/lib.sh
k -n argocd get applications
k -n argocd get application storefront-api -o jsonpath='{.status.sync.status} {.status.health.status}{"\n"}'
# force an immediate refresh instead of waiting for the poll:
k -n argocd annotate application storefront-api argocd.argoproj.io/refresh=hard --overwrite
# what exactly runs in prod (always a digest):
k -n prod get pods -o jsonpath='{..image}'; echo
```

If the digest in `deploy/prod/kustomization.yaml` is still the all-zero placeholder, the Application stays unhealthy: there is no such image. That is expected in a fresh fork before the first release.

## Common mistakes

- Treating the GitOps controller as a security boundary. Anyone with write access to the deploy folder controls what Argo CD applies; admission control is what stops a bad commit.
- `maxUnavailable` above 0 for important services: a blocked rollout would then remove healthy pods.
- Using tags in the GitOps folder: the cluster could run different content without any commit.
- Fixing production with `kubectl edit`: `selfHeal` undoes it, and the change is not reviewed.

## Check yourself

1. A malicious commit changes the prod digest to a tampered image. What do Argo CD and Kyverno each do?
2. Why does production keep serving during that attack?
3. How do you roll back a bad release in this project?

### Answers

<details><summary>Answers</summary>

1. Argo CD applies the commit: it tries to update the Deployment. Kyverno refuses that update because the image is not signed by the release workflow, so the sync fails with the policy message in Argo CD's sync result, and the alert `UntrustedWorkloadBlocked` fires. The old Deployment and its pods stay as they were.
2. The Deployment update itself was refused, so nothing changed in the cluster. Even if a new ReplicaSet were created some other way, `maxUnavailable: 0` keeps old pods until new ones are ready, and the new ones would never be admitted.
3. `git revert` the `deploy: storefront-api <digest>` commit. Argo CD deploys the previous digest, which is still signed and verifiable.

</details>
