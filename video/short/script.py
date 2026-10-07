"""The 1-minute vertical short: one entry per voiceover line (see build_short.py).

`say` is the caption; the spoken text is in voiceover/lines.json. Numbers are from docs/test-results.md
(release run 37119604685) and the real Grafana capture in docs/images/.
"""

from parts import crop, end_card, logo, stats, term

NAME = "supply-chain-short"
HEADER = {"logo": "kubernetes-icon-color.svg", "topic": "Kubernetes supply chain", "sub": "only signed images run"}
DASH = "../../docs/images/grafana-dashboard.png"

LINES = [
    {"id": "c01", "say": "Someone stole our registry password and pushed their own image. Production refused it in 2 seconds.",
     "sfx": "error", "body": """
<div class="stamp bad" data-at="-1">STOLEN PASSWORD</div>
<div class="label dim" data-at="-1">🔑 → 📦 REGISTRY → <img class="inl" src="logos/kubernetes-icon-color.svg">PRODUCTION</div>
<div class="big ok" data-at="3.2"><span data-count="2">2</span><small>s</small></div>
<div class="label ok" data-at="3.4">REFUSED BY THE CLUSTER</div>"""},
    {"id": "c02", "say": "Nobody had to notice.", "sfx": "pop", "body": """
<div class="emoji" data-at="0">🛡️</div><div class="label" data-at="0.2">0 HUMANS NEEDED</div>"""},
    {"id": "c03", "say": "Here's the problem. Kubernetes runs whatever image sits in your registry, as long as the token is valid.",
     "sfx": "scene", "body": logo("kubernetes-icon-color.svg", "Kubernetes trusts it") + """
<div class="users" data-at="1.5">📦 registry → ☸️ cluster</div>
<div class="label amber" data-at="3.4">VALID TOKEN = IT RUNS</div>"""},
    {"id": "c05", "say": "So every image my pipeline builds gets signed by the release workflow itself. No private key anywhere.",
     "sfx": "chapter", "body": logo(None, "🔏 Sigstore keyless signing") + """
<div class="title" data-at="0.8">Signed by<br><span class="ok">the pipeline</span></div>
<div class="label dim" data-at="4.4">NO PRIVATE KEY TO STEAL</div>"""},
    {"id": "c06", "say": "Plus three signed papers: where it was built, a vulnerability scan, and a list of every library inside.",
     "sfx": "scene", "body": """
<div class="checks"><div class="check" data-at="0.8">📜 provenance <span>where it was built</span></div>
<div class="check" data-at="2.2">🔍 Trivy scan <span>0 critical</span></div>
<div class="check" data-at="3.6">🧾 SBOM <span>every library</span></div></div>"""},
    {"id": "c07", "say": "At the cluster door, Kyverno checks all of it, before any pod can start.", "sfx": "scene",
     "body": logo("kyverno-icon-color.svg", "Kyverno at the door") + """
<div class="emoji" data-at="1.0">🚪</div><div class="label amber" data-at="2.0">NO VALID PAPERS → NO POD</div>"""},
    {"id": "c08", "say": "Then I attack it. 7 different ways, on every single release.", "sfx": "chapter",
     "body": logo("grafana-icon.svg", "Grafana · real run", 0, 72) + crop(DASH, 40, 100, 760, 185, 1000, 1600) + """
<div class="label bad" data-at="1.2">7 ATTACKS ON EVERY RELEASE</div>"""},
    {"id": "c09", "say": "An image from another registry? Refused in under half a second.", "sfx": "pop", "body": """
<div class="label dim" data-at="0">🌍 IMAGE FROM ANOTHER REGISTRY</div>
<div class="big ok" data-at="1.8">484<small>ms</small></div><div class="label ok" data-at="2.0">REFUSED</div>"""},
    {"id": "c10", "say": "Unsigned, pushed with a stolen token? Refused in 2 seconds.", "sfx": "pop", "body": """
<div class="label dim" data-at="0">🔑 UNSIGNED · STOLEN TOKEN</div>
<div class="big ok" data-at="1.8">2<small>s</small></div><div class="stamp bad" data-at="2.0">REFUSED</div>"""},
    {"id": "c11", "say": "The scary one: a perfectly valid signature, from the wrong workflow. Still refused.", "sfx": "error",
     "body": term([(0.6, "✔ signature verified", "g"),
                   (1.8, "certificate subject: …/workflows/e2e.yaml@refs/heads/main", "r"),
                   (2.6, "required subject:    …/workflows/release.yaml@refs/heads/main", "g")], "kyverno: verify-release-images") + """
<div class="stamp bad" data-at="3.6">STILL REFUSED</div>"""},
    {"id": "c12", "say": "A malicious commit to git? Argo CD applied it. The cluster refused it 6 seconds later.", "sfx": "scene",
     "body": logo("argo-icon-color.svg", "Argo CD applied the commit") + """
<div class="big ok" data-at="2.6">6<small>s</small></div><div class="label ok" data-at="2.8">REFUSED · PROD KEPT SERVING</div>"""},
    {"id": "c13", "say": "And the real release? Admitted, every single time.", "sfx": "success", "body": """
<div class="emoji" data-at="0">✅</div><div class="title" data-at="0.6">Real release:<br><span class="ok">admitted</span></div>
<div class="label dim" data-at="1.6">EVERY SINGLE TIME</div>"""},
    {"id": "c14", "say": "The full project is free. Follow, and I'll show you how to build it.", "sfx": "outro",
     "body": end_card(["kubernetes-icon-color.svg", "kyverno-icon-color.svg", "argo-icon-color.svg",
                       "prometheus-icon-color.svg"], "Full DevSecOps project")},
]
