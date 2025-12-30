# YouTube Reels Pipeline

## Overview

The YouTube Reels Pipeline is a production-grade solution for generating highlight videos (≤ 60 seconds) from YouTube URLs, complete with subtitles. The pipeline leverages YouTube subtitles or Whisper transcription, and optionally supports machine translation for multilingual subtitles. This project is distributed as source code, not as a standalone executable, for maximum flexibility and alignment with studio workflows.

## Rationale for Source Distribution

This pipeline is intentionally distributed as source code rather than a monolithic executable to provide:

- **Lightweight Setup:** Avoids large binary distributions (4–8GB executables).
- **Flexible GPU/CUDA Support:** Seamless adaptation to your hardware and CUDA environment.
- **Simple Model Management:** Facilitates straightforward model upgrades and customizations.
- **Professional Workflow Integration:** Mirrors internal tools and workflows employed in professional studio environments.

## Features

- End-to-end highlight extraction for short-form content from a single YouTube URL.
- Automatic subtitle handling (YouTube subtitles or Whisper transcription).
- Optional subtitle translation using NLLB models.
- All outputs are structured and organized under a dedicated workspace directory.

## Usage Scenarios

This project delivers not just code, but a solution refined by considerable engineering and design:

- Save weeks of development and experimentation.
- Leverage a pre-designed and validated pipeline architecture used in real production.
- Benefit from comprehensive documentation, structure, and example-driven guidance.

## Requirements

- **Python:** 3.11 or higher
- **External Tools:** 
  - `yt-dlp`
  - `ffmpeg` (must be available in your system PATH)
- **Python Dependencies:** 
  - PyAV (requires compatible ffmpeg libraries for your OS)
  - For translation functionality: `transformers`, `torch`, `sentencepiece`

## Quick Start

### Installation

```bash
pip install -e .
```

### Basic Workflow

#### Standard Processing

```bash
reels ingest https://www.youtube.com/watch?v=VIDEO_ID
reels build VIDEO_ID
```

#### Ingest with Translation (Example: Korean)

```bash
reels ingest https://www.youtube.com/watch?v=VIDEO_ID --translate ko
```

#### Build with Translated Subtitles

```bash
reels build VIDEO_ID --translated-lang ko
```

**Note:**  
- Translation uses `facebook/nllb-200-distilled-600M`.  
- NLLB language codes are required (e.g., `ko` → `kor_Hang`, `en` → `eng_Latn`).

## CLI Options

### `reels ingest`
- `--workspace <path>`: Set a custom workspace root.
- `--translate <lang>`: Translate subtitles during ingest (e.g., `ko`, `ja`, `en`).

### `reels build`
- `--workspace <path>`: Set a custom workspace root.
- `--style <style_id>`: Subtitle style preset (default: `reels_default`).
- `--title <text>`: Add a title overlay.
- `--tagline <text>`: Add a tagline overlay.
- `--watermark <text>`: Add a watermark text overlay.
- `--translated-lang <lang>`: Render translated subtitles below the original.
## Output Structure

All pipeline data is stored under a `workspace` directory (which is typically `.gitignored`). Example layout for an asset with ID `<ASSET_ID>`:

- `workspace/assets/<ASSET_ID>/source/video.mp4`
- `workspace/assets/<ASSET_ID>/subtitles/original.srt`
- `workspace/assets/<ASSET_ID>/subtitles/translated_ko.srt` (if translated)
- `workspace/assets/<ASSET_ID>/derived/shots.json`
- `workspace/assets/<ASSET_ID>/derived/highlight.json`
- `workspace/assets/<ASSET_ID>/derived/styled.ass`
- `workspace/assets/<ASSET_ID>/output/reel_60s.mp4`

## Troubleshooting

- **ffmpeg errors:** Ensure `ffmpeg` is installed and available on your system PATH.
- **PyAV errors:** Install the correct ffmpeg libraries for your OS, and reinstall the `av` Python package if needed.
- **Missing subtitles:** The pipeline uses either available YouTube subtitles or Whisper transcription, depending on availability.


