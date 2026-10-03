If someone stole your container registry password tonight, could they run their own code in your production cluster? 🤔

For most Kubernetes clusters the honest answer is yes. The cluster trusts whatever image sits in "our" registry. In 2026 attackers got there in three ways:
👉 malicious workflows injected into thousands of GitHub repos
👉 popular GitHub Action tags quietly moved to malicious commits
👉 stolen registry tokens used to push images under the same name

So I built a project where production only runs code it can PROVE came from us 🔏

Think of sealed medicine 💊 Every image our pipeline builds gets 4 signed papers:
1️⃣ a seal: signed by our release workflow, with no secret keys to steal (Sigstore)
2️⃣ an origin certificate: which repo and commit it came from (SLSA provenance)
3️⃣ a lab test: a signed scan with 0 critical or high vulnerabilities
4️⃣ an ingredient list: every library inside (SBOM)

At the door of the cluster, a pharmacist (Kyverno) checks all four before any pod starts. No valid papers, no pod.

🧪 Then I attacked it myself, on a fresh cluster, on every release (GitHub Actions):
🌍 image from another registry: refused in 0.5 s
🔑 unsigned image pushed with a stolen token: refused in 2.1 s
🧬 tampered copy of our image: refused in 2.0 s
🦈 image with a VALID signature from an injected workflow + forged provenance: refused in 2.0 s
👑 our own image, but privileged: refused in 0.4 s
🐙 malicious digest committed to git: Argo CD applied it, the cluster refused it 6 s after the push, and the service never went down
🕳️ an old image with known CVEs already running: Trivy Operator found it and an alert fired

Only after every attack fails does the pipeline promote the new release to production.

📚 New to DevOps security? I wrote a free study guide for this project. It explains every piece from zero (container images, Sigstore, SLSA, SBOMs, Kyverno, GitOps, GitHub Actions hardening) with 9 hands-on labs and 25 interview questions. It's also a 60-page PDF.

👉 Swipe through the slides: the problem, the idea, the architecture, the checks and the measured results.

💻 Code + study guide: https://github.com/sufyanahmadkamboh/sufyan-devops-secure-supply-chain
🌐 Slides + all my projects: https://sufyanahmadkamboh.github.io/#story=secure-supply-chain&slide=1

With your registry password, could someone run their code in your cluster? Tell me honestly 👇

#DevOps #SupplyChainSecurity #Kubernetes #DevSecOps #Sigstore #SLSA #SBOM #Kyverno #GitOps #PlatformEngineering
