# 1-minute short (vertical)

A 59-second vertical video (1080×1920, 30 fps) for YouTube Shorts, Instagram Reels and TikTok, built from code
like the long video. It opens on the measured result ("Someone stole our registry password and pushed their own image. Production refused it in 2 seconds."), then shows the problem, the idea and the proof from
the real test results, and ends with a call to follow.

| File | What it is |
|---|---|
| `script.py` | the script: one entry per voiceover line, with the caption text, the visual and its sound effect |
| `parts.py` | building blocks for the visuals: screenshot crops, tool logos, terminal lines, the DevOps loop, the end card |
| `build_short.py` | the pipeline: voiceover → timeline → animated page → frames → voice + sound effects (no music) → MP4 |
| `render.mjs` | renders every frame with headless Edge: the page exposes `render(t)`, each frame sets the time |
| `voiceover/` | the recorded voiceover (SpeakSay, voice "Steve"): one FLAC per line, `lines.json` (the exact spoken text and settings) and `words.json` (word timings for the captions) |
| `logos/` | Kubernetes, Kyverno, Prometheus and Argo icons from the CNCF artwork repository; the Grafana icon from the Grafana repository |
| `upload.md` | title, description and hashtags for the upload |

```bash
python video/short/build_short.py   # -> video/out/short/supply-chain-short-{full,silent}.mp4
```

How it holds attention:
- The first frame already shows the result; the voice starts at 0 s.
- The topic is clear on every frame: a header with "DevSecOps" and "Kubernetes supply chain", and the logo of each tool where it acts.
- A new visual on every line, a sound effect on every cut, and big word-by-word captions (works without sound).
- Real numbers and log lines from `docs/test-results.md` and `reports/`; the dashboard is the real Grafana capture in
  `docs/images/`. The voice runs 7% faster than recorded (pitch kept).

Requirements: Python 3 with numpy and scipy, Node.js 22+, Microsoft Edge, Docker (ffmpeg pinned by digest).
The sound effects come from `../sound_effects.py` (synthesised; see `../AUDIO-LICENSES.md`).
