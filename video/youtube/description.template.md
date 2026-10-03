Could a stolen registry password run code in your Kubernetes cluster? In this full DevOps project I build a zero-trust software supply chain: production only runs container images that your own GitHub Actions release pipeline built, scanned and signed, checked at admission by Kyverno with Sigstore keyless signatures, SLSA provenance, a signed vulnerability scan and an SBOM. Then I attack it 7 ways on every release and show the measured results.

💻 Code: https://github.com/sufyanahmadkamboh/sufyan-devops-secure-supply-chain
📚 Free study guide (60-page PDF, 9 labs, 25 interview questions): https://github.com/sufyanahmadkamboh/sufyan-devops-secure-supply-chain/tree/main/study
📈 Measured test results: https://github.com/sufyanahmadkamboh/sufyan-devops-secure-supply-chain/blob/main/docs/test-results.md
🧪 The CI run behind the numbers: https://github.com/sufyanahmadkamboh/sufyan-devops-secure-supply-chain/actions/runs/37119604685
🌐 All my projects: https://sufyanahmadkamboh.github.io/#story=secure-supply-chain&slide=1

⏱️ Chapters
{{CHAPTERS}}

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
