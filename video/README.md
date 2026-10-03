# Video tutorial

A 28-minute explainer of this project, built entirely from code: every frame is an HTML scene rendered by a
headless browser, the narration uses the Windows speech engine, and ffmpeg assembles the result.

| File | What it is |
|---|---|
| `scenes.py` | the script: 37 scenes, 155 narration steps, and the visuals for each step |
| `components.py` | building blocks: cards, tiles, diagrams, highlighted code excerpts |
| `build.py` | the pipeline: page → frames → narration → encode → captions and chapters |
| `shot.mjs` | screenshots the scenes with one headless Edge/Chrome (DevTools protocol) |
| `tts.ps1` | narrates each step offline with `System.Speech` |
| `thumbnail.html` | the YouTube thumbnail (1280×720) |
| `youtube/` | upload package: title options, description (with chapters), tags, captions (SRT), thumbnail, pinned comment |

## Build

Requirements: Windows (for `System.Speech`), Python 3 with `pygments` and `Pillow`, Node.js 22+, Microsoft Edge
(or set `BROWSER`), and Docker (ffmpeg runs in a container pinned by digest).

```bash
python video/build.py            # everything, about 7 minutes; output: video/out/video.mp4
python video/build.py frames     # only re-render the visuals after editing scenes.py
python video/build.py audio      # only re-narrate (VOICE="Microsoft Zira Desktop" SPEED=1 to change the voice)
python video/build.py video      # only re-encode, and rewrite captions, chapters and the description
```

How it fits together:
- Each narration step becomes one frame. Elements marked `data-s="n"` appear at step `n`, and the newest one is
  highlighted. Code excerpts highlight the lines the narration talks about.
- Each step's frame stays on screen exactly as long as its narration plus a short pause, rounded to whole video
  frames. The audio track is built from the same timings, so picture and voice cannot drift apart.
- Captions come from the same text as the narration, split into sentences and timed in proportion to their length.
- Words the speech engine would mispronounce (Kyverno, SBOM, kubectl, …) are respelled for the voice only
  (`PRONOUNCE` in `build.py`). The captions keep the real spelling.
- Audio is compressed and limited to about −15 LUFS, close to YouTube's playback loudness.

## Facts in the video

Every number comes from `docs/test-results.md` (release run 37119604685). Every code excerpt is shortened from the
real file named in its title bar; `…` marks a cut.

## Upload checklist

1. Upload `out/video.mp4`, and use the first title in `youtube/title.txt`.
2. Paste `youtube/description.md` as the description. Its chapter list turns into YouTube chapters.
3. Set `youtube/thumbnail.png` as the thumbnail, and add the tags from `youtube/tags.txt`.
4. Under Subtitles, upload `youtube/captions.srt` (English), so captions are accurate and searchable.
5. After publishing, pin the comment in `youtube/pinned-comment.txt`.
6. Add an end screen pointing to the next project or a playlist.
