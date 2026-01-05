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
        if _is_subtitle_download_error(exc):
            downloaded = _find_downloaded_video(video_path) or video_path
        else:
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


def _is_subtitle_download_error(exc: Exception) -> bool:
    message = _strip_ansi(str(exc)).lower()
    return "subtitle" in message


def _find_downloaded_video(video_path: Path) -> Optional[Path]:
    if video_path.exists():
        return video_path
    for candidate in video_path.parent.glob(f"{video_path.stem}.*"):
        if candidate.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov"}:
            return candidate
    return None


def _strip_ansi(text: str) -> str:
    return "".join(ch for ch in text if ch.isprintable())
