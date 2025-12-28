# YouTube Reels MVP

Minimal, structure-first MVP that turns a YouTube URL into a single <=60s highlight.

## What it does
- Input: YouTube URL
- Output: One highlight video under 60 seconds
- Subtitles: Uses YouTube-provided subtitles only (no translation)
- Processing: PyAV for shot detection, ffmpeg for render
- Highlighting: Scores shots by motion + audio energy and picks the best <=60s combo

## Requirements
- Python 3.10+
- `yt-dlp` and `ffmpeg` available on PATH
- PyAV dependencies installed (ffmpeg libraries for your OS)

## Install
```bash
pip install -e .
```

## Quick start
```bash
reels ingest <youtube_url>
reels build <asset_id>
```

## CLI usage
Ingest a video and generate shot data:
```bash
reels ingest https://www.youtube.com/watch?v=VIDEO_ID
```

Build a 60s reel from an existing asset:
```bash
reels build YT_VIDEO_ID
```

Optional build flags:
```bash
reels build YT_VIDEO_ID --style reels_default --title "Main Title" --tagline "Short tagline"
reels build YT_VIDEO_ID --watermark "MY BRAND"
```

## Output layout
Everything lives under `workspace/` (gitignored):
- `workspace/assets/<ASSET_ID>/source/video.mp4` (downloaded video)
- `workspace/assets/<ASSET_ID>/subtitles/original.srt`
- `workspace/assets/<ASSET_ID>/derived/shots.json` (shot list + scores)
- `workspace/assets/<ASSET_ID>/derived/highlight.json` (selected shots)
- `workspace/assets/<ASSET_ID>/derived/styled.ass` (styled subtitles)
- `workspace/assets/<ASSET_ID>/output/reel_60s.mp4` (final output)

See `docs/아키텍처.md` for more details.

## How shot selection works
1. Ingest: detect shots using frame differences (visual motion) and audio energy.
2. Each shot gets a score (motion + audio weights).
3. Build: select the highest-score combination that fits <=60s.

## Subtitles
- Karaoke timing is generated from word durations.
- Energy-based coloring can be enabled via `reels/styles/reels_default.json`.
- Subtitles are clipped and time-shifted to match the selected shots.

## Troubleshooting
- ffmpeg errors: confirm `ffmpeg` is on PATH.
- PyAV errors: install ffmpeg libraries for your OS and reinstall `av`.
- Missing subtitles: the pipeline uses YouTube subtitles only.
