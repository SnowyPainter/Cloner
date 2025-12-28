from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from reels.utils.fs import ensure_dir


class YtDlpError(RuntimeError):
    pass


def download_youtube(url: str, video_path: Path, subtitles_dir: Path) -> Optional[Path]:
    ensure_dir(video_path.parent)
    ensure_dir(subtitles_dir)

    output_template = str(video_path.with_suffix(".%(ext)s"))
    try:
        from yt_dlp import YoutubeDL
    except Exception as exc:
        raise YtDlpError("yt-dlp Python package is required") from exc

    opts = {
        "format": "mp4",
        "merge_output_format": "mp4",
        "outtmpl": output_template,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitlesformat": "srt",
        "writeinfojson": True,
    }

    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            downloaded = Path(ydl.prepare_filename(info))
    except Exception as exc:
        raise YtDlpError(str(exc)) from exc

    if downloaded.exists() and downloaded != video_path:
        downloaded.replace(video_path)

    srt = _find_first_srt(video_path.parent)
    if srt:
        target = subtitles_dir / "original.srt"
        shutil.move(str(srt), target)
        return target
    return None


def _find_first_srt(directory: Path) -> Optional[Path]:
    for path in directory.glob("*.srt"):
        return path
    return None
