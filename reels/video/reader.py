from __future__ import annotations

from pathlib import Path


class VideoReaderError(RuntimeError):
    pass


def _open_container(path: Path):
    try:
        import av
    except Exception as exc:  # pragma: no cover - dependency missing
        raise VideoReaderError("PyAV is required for video processing") from exc

    return av.open(str(path))


def get_duration_seconds(path: Path) -> float:
    with _open_container(path) as container:
        if container.duration is not None:
            return float(container.duration / 1_000_000)
        if container.streams.video:
            stream = container.streams.video[0]
            if stream.duration is not None and stream.time_base is not None:
                return float(stream.duration * stream.time_base)
    return 0.0


def has_audio(path: Path) -> bool:
    with _open_container(path) as container:
        return bool(container.streams.audio)
