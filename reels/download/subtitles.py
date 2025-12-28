from __future__ import annotations

from pathlib import Path


class SubtitleError(RuntimeError):
    pass


def require_subtitles(path: Path) -> Path:
    if not path.exists():
        raise SubtitleError("YouTube subtitles not found")
    return path
