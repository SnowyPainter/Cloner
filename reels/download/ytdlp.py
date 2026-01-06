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

    try:
        from yt_dlp import YoutubeDL
    except Exception as exc:
        raise YtDlpError("yt-dlp Python package is required") from exc

    def _download(write_subtitles: bool) -> Path:
        opts = _build_opts(video_path, write_subtitles=write_subtitles)
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return Path(ydl.prepare_filename(info))

    try:
        downloaded = _download(write_subtitles=True)
    except Exception as exc:
        if _is_subtitle_download_error(exc):
            downloaded = _find_downloaded_video(video_path)
            if not downloaded or not downloaded.exists():
                downloaded = _download(write_subtitles=False)
        else:
            raise YtDlpError(str(exc)) from exc

    if downloaded and downloaded.exists() and downloaded != video_path:
        downloaded.replace(video_path)

    if not video_path.exists():
        raise YtDlpError("YouTube download did not produce a video file.")

    srt = _find_first_srt(video_path.parent)
    if srt:
        target = subtitles_dir / "original.srt"
        shutil.move(str(srt), target)
        return target
    return None


def _build_opts(video_path: Path, write_subtitles: bool) -> dict:
    output_template = str(video_path.with_suffix(".%(ext)s"))
    opts = {
        "format": (
            "bv*[height<=1080][ext=mp4]+ba[ext=m4a]"
            "/b[height<=1080][ext=mp4]"
            "/b[height<=1080]"
        ),
        "merge_output_format": "mp4",
        "outtmpl": output_template,
        "writeinfojson": True,
    }
    if write_subtitles:
        opts.update(
            {
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitlesformat": "srt",
            }
        )
    return opts


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
