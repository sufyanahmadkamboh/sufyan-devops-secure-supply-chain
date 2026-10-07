Could a stolen registry password run code in your Kubernetes cluster? In this full DevOps project I build a zero-trust software supply chain: production only runs container images that your own GitHub Actions release pipeline built, scanned and signed, checked at admission by Kyverno with Sigstore keyless signatures, SLSA provenance, a signed vulnerability scan and an SBOM. Then I attack it 7 ways on every release, show the measured results, and walk you through running and attacking it on your own laptop.

💻 Code: https://github.com/sufyanahmadkamboh/sufyan-devops-secure-supply-chain
📚 Free study guide (60-page PDF, 9 labs, 25 interview questions): https://github.com/sufyanahmadkamboh/sufyan-devops-secure-supply-chain/tree/main/study
📈 Measured test results: https://github.com/sufyanahmadkamboh/sufyan-devops-secure-supply-chain/blob/main/docs/test-results.md
🧪 The CI run behind the numbers: https://github.com/sufyanahmadkamboh/sufyan-devops-secure-supply-chain/actions/runs/37119604685
🌐 All my projects: https://sufyanahmadkamboh.github.io/#story=secure-supply-chain&slide=1

🧪 Run it on your laptop (Docker, kind, git, Bash; about 4 minutes, no cloud account):
git clone https://github.com/sufyanahmadkamboh/sufyan-devops-secure-supply-chain.git
cd sufyan-devops-secure-supply-chain && scripts/platform-up.sh
scripts/try.sh verify | trusted | foreign | unsigned | privileged | sandbox | scan | alerts | dashboard

⏱️ Chapters
0:00 The question
1:34 Why: the problem
2:40 The idea
3:35 Architecture
4:40 Tool 1: Docker & distroless
5:27 Tool 2: GitHub Actions
7:14 Tool 3: Trivy
7:47 Tool 4: Syft (SBOM)
8:21 Tool 5: SLSA provenance
9:02 Tool 6: Sigstore cosign
10:16 Tool 7: GHCR & digests
10:51 Tool 8: Kyverno
13:13 Rollout: audit first
13:49 Tool 9: Argo CD & Kustomize
15:00 Tool 10: Trivy Operator
15:32 Tool 11: Prometheus & Grafana
17:29 Tool 12: the attack test
19:02 Measured results
19:53 Hands-on: run it on your laptop
24:55 Use it in production
26:13 Limitations & next steps
26:44 Summary & resources

🧰 Tools used, and what each one does here
• Docker + distroless: a 3.7 MB, non-root image with base images pinned by digest
• GitHub Actions: the hardened release pipeline (SHA-pinned actions, least-privilege tokens, OIDC)
• Trivy: a vulnerability gate, plus a signed scan report
• Syft: the SBOM (CycloneDX)
• SLSA v1 provenance: repository, branch, commit and run of every build
• Sigstore cosign, Fulcio, Rekor: keyless signatures and attestations
• GitHub Container Registry: images, signatures and attestations by digest
• Kyverno 1.19 (ImageValidatingPolicy, ValidatingPolicy) + Pod Security Admission: the guard at the cluster door
• Argo CD + Kustomize: GitOps delivery of the verified digest
• Trivy Operator: re-scans running images for new CVEs
• Prometheus + Grafana: alerts and a dashboard as code
• kind: a fresh cluster for the end-to-end attack test on every release

📊 Measured on GitHub Actions
• Image from another registry: refused in 484 ms
• Unsigned image pushed with a stolen token: refused in 2,058 ms
• Tampered copy of the trusted image: refused in 1,968 ms
• VALID signature from a different (injected) workflow + forged provenance: refused in 1,970 ms
• Trusted image as a privileged pod: refused in 363 ms
• Malicious digest committed to git: refused 6 s after the push, production kept serving
• Old image with known CVEs running: 27 CRITICAL found, alert fired

💬 Tell me in the comments: with your registry password, could someone run their code in your cluster?

#Kubernetes #DevSecOps #SupplyChainSecurity
