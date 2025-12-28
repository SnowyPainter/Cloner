# YouTube Reels MVP

Minimal, structure-first MVP that turns a YouTube URL into a single <=60s highlight.

## What it does
- Input: YouTube URL
- Output: One highlight video under 60 seconds
- Subtitles: Use only YouTube-provided subtitles (no translation)
- Processing: PyAV for shot detection, ffmpeg for render

## Commands
```bash
reels ingest <youtube_url>
reels build <asset_id>
```

## Workspace layout
Outputs land under `workspace/` (gitignored). See `docs/아키텍처.md` for details.

## Notes
- `yt-dlp` and `ffmpeg` must be installed and available on PATH.
- This MVP favors predictability over "best scene" selection.
